#!/bin/bash
# ===========================================
# @file run_perf.sh
# @brief Dockerized perf benchmarker for Monte Carlo simulation engine
# ===========================================
#
# Benchmarks simulation methods (SIMD, Pool, Heap, etc.) using `perf stat`,
# and logs system performance metrics to structured logs (Markdown, Parquet).
#
# === Metrics Logged ===
#
# ▸ Core Execution
#   - cycles:              Total CPU clock cycles consumed
#   - instr:               Total instructions executed
#   - ipc:                 Instructions per cycle (efficiency metric)
#   - cycles_per_trial:    Avg CPU cycles used per simulation trial
#
# ▸ Time
#   - wall_time_s:         Real-world elapsed time (sec)
#   - wall_time_ns:        Real-world elapsed time (nanoseconds, high-precision)
#
# ▸ Cache Accesses
#   - l1_loads:            L1 data cache load attempts
#   - l1_misses:           L1 cache load misses (ideal <5%)
#   - l2_loads:            L2 cache load attempts
#   - l2_misses:           L2 load misses
#   - l3_loads:            Last-level (L3) cache loads
#   - l3_misses:           L3 misses (fallback to RAM = slow)
#   - cache_loads:         Aggregated cache loads (all levels)
#   - cache_miss:          Aggregated cache misses
#
# ▸ Memory Paging
#   - tlb_loads:           TLB accesses (virtual → physical addr translation)
#   - tlb_misses:          TLB misses (page walk penalty; avoid if high)
#
# ▸ Branch Prediction
#   - branch_instr:        Total branch (if/loop/jump) instructions
#   - branch_misses:       Branch mispredictions (pipeline flush = stall)
#
# ▸ Derived
#   - miss_per_trial:      Cache+TLB misses per trial (normalized locality metric)
#
# ⚠️ L2/L3 CACHE STATS – IMPORTANT NOTE:
#
# Availability of L2/L3 performance events varies widely and depends on:
#   - 🏭 CPU Vendor: Intel vs AMD
#   - 🧠 Microarchitecture: (e.g., Intel Skylake, AMD Zen 3, Zen 4)
#   - 🧰 Kernel Version & Perf PMU Driver Support
#
# 🔍 Why L2/L3 Might Be Missing or Misleading:
#   - On **AMD Zen 4**, `perf list` often does **not expose L2 events** like `L2-dcache-loads` by default.
#     You may need to use **raw event codes** or **kernel patches** for full access.
#   - On **Intel CPUs**, many standard L2/L3 counters **do work**, but naming may differ (e.g., `LLC-*` for L3).
#   - Virtualization or container isolation can also **block PMU access**.
#
# ✅ What to Do:
#   1. Run `perf list | grep -i l2` and `perf list | grep -i l3` to check availability.
#   2. If benchmarking across vendors, expect **non-equivalent L2/L3 stats** and document accordingly.
#
# ✅ TL;DR:
#   L2/L3 metrics are **not portable**. Always **validate events per system** using:
#     $ perf list
#     $ lscpu    # for model name / microarchitecture
#
# === Usage ===
#   ./run_perf.sh                      # All methods, default trials
#   ./run_perf.sh 50000000            # All methods, custom trials
#   ./run_perf.sh SIMD                # Single method, default trials
#   ./run_perf.sh 50000000 Pool       # Custom trials + single method
#
# === Output ===
#   logs/batch_<BATCHID>/perf_<METHOD>_<BATCHID>.csv # RAW perf stat output
#   logs/batch_<BATCHID>/perf_<METHOD>_<TIMESTAMP>.parquet # Structured Parquet log
#   logs/batch_<BATCHID>/perf_results_<METHOD>_<TIMESTAMP>_<BATCHID>.parquet
#   perf_results_all_<BATCHID>.parquet # All methods ran per sim

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"

set -e

# -------- Config --------
DEFAULT_TRIALS=100000000
ALL_METHODS=("Sequential" "Heap" "Pool" "SIMD")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BATCHID=$(uuidgen | cut -d'-' -f1)
BUILD_PATH="./build/montecarlo"
GLOBAL_TIMESTAMP=$(date "+%Y-%m-%d_%H-%M-%S")

# -------- CLI Args --------
ARG1="$1"
ARG2="$2"

if [[ -z "$ARG1" && -z "$ARG2" ]]; then
    TRIALS=$DEFAULT_TRIALS
    METHODS=("${ALL_METHODS[@]}")
elif [[ "$ARG1" =~ ^[0-9]+$ && -z "$ARG2" ]]; then
    TRIALS="$ARG1"
    METHODS=("${ALL_METHODS[@]}")
elif [[ "$ARG1" =~ ^[a-zA-Z]+$ && -z "$ARG2" ]]; then
    TRIALS=$DEFAULT_TRIALS
    METHODS=("$ARG1")
else
    TRIALS="$ARG1"
    METHODS=("$ARG2")
fi

# -------- Info --------
echo "[INFO] Trials   : $TRIALS"
echo "[INFO] Methods  : ${METHODS[*]}"
echo "[INFO] Batch ID : $BATCHID"
echo "[INFO] Timestamp: $GLOBAL_TIMESTAMP"

LOG_DIR="db/logs/batch_${BATCHID}_${GLOBAL_TIMESTAMP}"
mkdir -p "$LOG_DIR"

# -------- Perf Event Creation --------
PERF_EVENTS=""
PERF_EVENTS+="cycles,instructions,"
PERF_EVENTS+="cache-references,cache-misses,"
PERF_EVENTS+="branch-instructions,branch-misses,"
PERF_EVENTS+="L1-dcache-loads,L1-dcache-load-misses,"
PERF_EVENTS+="dTLB-loads,dTLB-load-misses"

echo "[INFO] Using perf events:"
echo "$PERF_EVENTS" | tr ',' '\n' | sed 's/^/  - /'

# -------- Run Each Method --------
for METHOD in "${METHODS[@]}"; do
    METHOD_TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[▶] Running: $METHOD"

    LOG_PATH="$LOG_DIR/perf_${METHOD}_${METHOD_TIMESTAMP}.csv"
    PERF_PARQUET="$LOG_DIR/perf_results_${METHOD}_${METHOD_TIMESTAMP}_${BATCHID}.parquet"

    mkdir -p "$(dirname "$LOG_PATH")"

    START_NS=$(date +%s%N)
    perf stat -x, -o "$LOG_PATH" -e $PERF_EVENTS "$BUILD_PATH" "$TRIALS" "$METHOD" > /dev/null
    END=$(date +%s%N)

    WALL_NS=$((END - START_NS))
    WALL_S=$(awk "BEGIN {printf \"%.6f\", $WALL_NS / 1000000000}")

    # Pull metrics into shell vars
    eval "$(python3 pipeline/parse_perf_metrics.py "$LOG_PATH" "$TRIALS")"

    python3 pipeline/gen_perf_parquet_logs.py \
        --out_path "$PERF_PARQUET" \
        --wall_time_s "$WALL_S" \
        --wall_time_ns "$WALL_NS" \
        --timestamp "$METHOD_TIMESTAMP" \
        --batchid "$BATCHID" \
        --method "$METHOD" \
        --trials "$TRIALS" \
        --cycles "$CYCLES" \
        --instr "$INSTR" \
        --ipc "$IPC" \
        --cache_loads "$CACHE_LOADS" \
        --cache_miss "$CACHE_MISS" \
        --l1_loads "$L1_LOADS" \
        --l1_misses "$L1_MISSES" \
        --l2_loads "$L2_LOADS" \
        --l2_misses "$L2_MISSES" \
        --l3_loads "$L3_LOADS" \
        --l3_misses "$L3_MISSES" \
        --tlb_loads "$TLB_LOADS" \
        --tlb_misses "$TLB_MISSES" \
        --branch_instr "$BRANCH_INSTR" \
        --branch_misses "$BRANCH_MISSES" \
        --miss_per_trial "$MISS_PER_TRIAL" \
        --cycles_per_trial "$CYCLES_PER_TRIAL"
done

python3 pipeline/combine_batch_parquets.py \
  "$LOG_DIR" \
  "$LOG_DIR/perf_results_all_${BATCHID}.parquet"

python3 pipeline/write_to_clickhouse.py \
  --batchid "$BATCHID"
  
echo "[INFO] Simulation Finished:"
echo "     └─ Exported CSV & Parquet logs to  : $LOG_DIR"
echo "     └─ Combined batch Parquet logs  : $LOG_DIR/perf_results_all_${BATCHID}.parquet"

