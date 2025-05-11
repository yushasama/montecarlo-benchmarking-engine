#!/bin/bash
# ===========================================
# run_perf.sh - Dockerized perf benchmarker
# ===========================================
##
# @file run_perf.sh
# @brief Runs containerized perf stats on Monte Carlo simulation engine.
#
# Benchmarks methods (SIMD, Pool, Heap, etc.) using `perf stat`, extracts:
# - IPC
# - Cache + TLB Miss %
# - Wall time (sec + ns)
# - Cycles per trial
#
# Generates timestamped Markdown summary (perf_results_*.md).
# Also symlinks latest file as `perf_results.md`.
#
# ## Usage:
# ```bash
# ./run_perf.sh [TRIALS] [METHOD]
# ./run_perf.sh 100000000 SIMD
# ```
#
# ## Output:
# - Markdown: perf_results_TIMESTAMP.md
# - Logs: logs/METHOD_perf.txt
# - Table: perf_results.md (symlink to latest)
#

DEFAULT_TRIALS=100000000
METHODS=("Sequential" "Heap" "Pool" "SIMD")
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
OUTPUT_FILE="perf_results_$TIMESTAMP.md"
EVENTS="cycles,instructions,cache-references,cache-misses,branch-instructions,branch-misses,L1-dcache-loads,L1-dcache-load-misses,LLC-loads,LLC-load-misses,dTLB-loads,dTLB-load-misses,context-switches,page-faults"

# Parse arguments
if [[ "$1" =~ ^[0-9]+$ ]]; then
  TRIALS=$1
  METHOD=${2:-All}
else
  TRIALS=$DEFAULT_TRIALS
  METHOD=${1:-All}
fi

# Normalize method case
METHOD_CAP="$(tr '[:lower:]' '[:upper:]' <<< ${METHOD:0:1})${METHOD:1}"

# Info
echo "[INFO] Running benchmark(s) with $TRIALS trials"
echo "[INFO] Target: $METHOD_CAP"
echo

# Markdown header
if [[ "$METHOD_CAP" == "All" ]]; then
    cat <<EOL > $OUTPUT_FILE
# 🧠 Monte Carlo Performance Results

## Config
- Trials: $TRIALS
- Metrics: Full perf stat (L1, L2, branch, TLB, IPC, etc.)
- CPU: Docker Linux container
- Build: Clang++ -O3 -march=native

| Method | Cycles | Instr | IPC | Wall Time (s) | Wall Time (ns) | L1 Miss % | L2 Miss % | Branch Miss % | TLB Miss % | Misses/Trial | Cycles/Trial |
|--------|--------|-------|-----|----------------|----------------|-----------|-----------|----------------|------------|----------------|--------------|
EOL

fi

run_perf() {
    local METHOD_NAME=$1
    echo "[INFO] Running: $METHOD_NAME..."
    docker run --rm --privileged montecarlo-bench perf stat -e $EVENTS ./build/montecarlo $TRIALS $METHOD_NAME 2> logs/${METHOD_NAME}_perf.txt

    FILE=logs/${METHOD_NAME}_perf.txt

    cycles=$(grep -i 'cycles' $FILE | awk '{print $1}' | tr -d ,)
    instr=$(grep -i 'instructions' $FILE | awk '{print $1}' | tr -d ,)
    cache_miss=$(grep -i 'cache-misses' $FILE | awk '{print $1}' | tr -d ,)
    cache_refs=$(grep -i 'cache-references' $FILE | awk '{print $1}' | tr -d ,)
    branch_misses=$(grep -i 'branch-misses' $FILE | awk '{print $1}' | tr -d ,)
    branches=$(grep -i 'branch-instructions' $FILE | awk '{print $1}' | tr -d ,)
    l1_misses=$(grep -i 'L1-dcache-load-misses' $FILE | awk '{print $1}' | tr -d ,)
    l1_loads=$(grep -i 'L1-dcache-loads' $FILE | awk '{print $1}' | tr -d ,)
    l2_misses=$(grep -i 'LLC-load-misses' $FILE | awk '{print $1}' | tr -d ,)
    l2_loads=$(grep -i 'LLC-loads' $FILE | awk '{print $1}' | tr -d ,)
    tlb_misses=$(grep -i 'dTLB-load-misses' $FILE | awk '{print $1}' | tr -d ,)
    tlb_loads=$(grep -i 'dTLB-loads' $FILE | awk '{print $1}' | tr -d ,)

    ipc=$(echo "scale=2; $instr / $cycles" | bc)
    l1_rate=$(echo "scale=2; 100 * $l1_misses / $l1_loads" | bc)
    l2_rate=$(echo "scale=2; 100 * $l2_misses / $l2_loads" | bc)
    branch_rate=$(echo "scale=2; 100 * $branch_misses / $branches" | bc)
    tlb_rate=$(echo "scale=2; 100 * $tlb_misses / $tlb_loads" | bc)
    miss_per_trial=$(echo "scale=2; $cache_miss / $TRIALS" | bc)
    cycles_per_trial=$(echo "scale=2; $cycles / $TRIALS" | bc)

    task_clock_ms=$(grep -i 'task-clock' $FILE | awk '{print $1}' | tr -d ,)
    wall_time_s=$(echo "scale=6; $task_clock_ms / 1000" | bc)
    wall_time_ns=$(echo "$task_clock_ms * 1000000" | bc)

    # Append to Markdown
    echo "| $METHOD_NAME | $cycles | $instr | $ipc | $wall_time_s | $wall_time_ns | ${l1_rate}% | ${l2_rate}% | ${branch_rate}% | ${tlb_rate}% | $miss_per_trial | $cycles_per_trial |" >> $OUTPUT_FILE
}

mkdir -p logs

# Run one method or all
if [[ "$METHOD_CAP" == "All" ]]; then
    for M in "${METHODS[@]}"; do
        run_perf "$M"
    done
else
    run_perf "$METHOD_CAP"
fi

echo "[✅] Benchmarking complete! Check perf_results.md"

ln -sf "$OUTPUT_FILE" perf_results.md
