#!/bin/bash
# ===========================================
# run_perf.sh
# ===========================================

## \file run_perf.sh
## \brief Dockerized perf benchmarker for Monte Carlo simulation engine
##
## \details
## Benchmarks simulation methods (SIMD, Pool, Heap, etc.) using `perf stat`,
## and logs system performance metrics to structured logs (CSV, Parquet).
##
## === Metrics Logged ===
##
## Core Execution
##   - cycles:              Total CPU clock cycles consumed
##   - instr:               Total instructions executed
##   - ipc:                 Instructions per cycle (efficiency metric)
##   - cycles_per_trial:    Avg CPU cycles used per simulation trial
##
## Time
##   - wall_time_s:         Real-world elapsed time (sec)
##   - wall_time_ns:        Real-world elapsed time (nanoseconds, high-precision)
##
## Cache Accesses
##   - l1_loads:            L1 data cache load attempts
##   - l1_misses:           L1 cache load misses (ideal <5%)
##   - l2_loads:            L2 cache load attempts (may not be supported)
##   - l2_misses:           L2 cache load misses (may not be supported)
##   - l3_loads:            Last-level (L3) cache loads (may not be supported)
##   - l3_misses:           L3 misses (fallback to RAM = slow, may not be supported)
##   - cache_loads:         Aggregated cache loads
##   - cache_miss:          Aggregated cache misses
##
## Memory Paging
##   - tlb_loads:           TLB accesses (address translation)
##   - tlb_misses:          TLB misses (page walk penalty)
##
## Branch Prediction
##   - branch_instr:        Total branch instructions
##   - branch_misses:       Branch mispredictions (pipeline flushes)
##
## Derived
##   - miss_per_trial:      Cache+TLB misses per trial (normalized locality metric)
##
## === Compatibility Notes (L2/L3 Caveats) ===
##
## Some performance counters are not consistently available across systems:
##   - Intel: L2/L3 counters usually available as `L2-dcache-*`, `LLC-*`
##   - AMD:   L2/L3 counters may be missing (Zen 3/4); use `perf list` to verify
##   - Virtual machines and containers may block PMU access
##
## Always validate support using:
##   $ perf list | grep -i l2
##   $ lscpu     # check microarchitecture
##
## === ClickHouse Integration ===
##
## By default, results are inserted into ClickHouse at the end of each batch run.
## To enable this:
##   - You must first run: `make init` (first time setup) or `make up` (to start services)
##   - Requires Docker and a running ClickHouse instance
##
## To skip ClickHouse insertion (e.g., CI, dry runs):
##   ./run_perf.sh 50000000 SIMD insert_db=false
##
## === Usage ===
##   ./run_perf.sh                             # Run all methods with default trials, insert to DB
##   ./run_perf.sh 50000000                    # All methods, custom trials
##   ./run_perf.sh SIMD                        # Single method, default trials
##   ./run_perf.sh 50000000 Pool               # Custom trials and single method
##   ./run_perf.sh 50000000 SIMD insert_db=false  # Run without inserting to ClickHouse
##
## === Output Files ===
##   db/logs/batch_<BATCHID>/perf_<METHOD>_<TIMESTAMP>.csv
##     → Raw perf stat output
##
##   db/logs/batch_<BATCHID>/perf_results_<METHOD>_<TIMESTAMP>_<BATCHID>.parquet
##     → Parsed structured metrics for that method
##
##   db/logs/batch_<BATCHID>/perf_results_all_<BATCHID>.parquet
##     → Combined metrics across all methods (for analysis or dashboarding)


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
ARG3="$3"

INSERT_DB=true

if [[ "$ARG3" == "insert_db=false" ]]; then
    INSERT_DB=false
fi

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

if [ "$INSERT_DB" = true ]; then
    python3 pipeline/insert_to_clickhouse.py \
    --batchid "$BATCHID"
else
  echo "[INFO] Skipping ClickHouse insertion (insert_db=false)"
fi

echo "[INFO] Simulation Finished:"
echo "     └─ Exported CSV & Parquet logs to  : $LOG_DIR"
echo "     └─ Combined batch Parquet logs  : $LOG_DIR/perf_results_all_${BATCHID}.parquet"

