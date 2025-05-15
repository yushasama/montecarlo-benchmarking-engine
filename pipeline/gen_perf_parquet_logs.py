# ===========================================
# gen_perf_parquet_logs.py
# ===========================================
##
# @file gen_perf_parquet_logs.py
# @brief Generates perf benchmarking parquet from command-line arguments.
#
# Accepts raw performance metrics from `perf stat` as arguments.
# Computes % miss rates for cache levels and TLB, as well as misses per trial.
# Saves results to a timestamped `.parquet` file in a structured batch directory,
# and also generates a global merged file if needed.
#
# ## Usage (example):
# ```bash
# python3 gen_perf_parquet_logs.py \
#   --out_path "db/logs/batch_<BATCHID>/perf_results_<METHOD>_<TIMESTAMP>_<BATCHID>.parquet" \
#   --timestamp "2025-05-13_17-00-20" \
#   --batchid "a7d38b57" \
#   --method "SIMD" \
#   --trials 100000000 \
#   --cycles 6010711137 \
#   --instr 8123412345 \
#   --ipc 1.35 \
#   --wall_time_s 0.08058 \
#   --wall_time_ns 80587148 \
#   --cache_loads 100000 \
#   --cache_miss 5000 \
#   --l1_loads 10000000 \
#   --l1_misses 30000 \
#   --l2_loads 200000 \
#   --l2_misses 10000 \
#   --l3_loads 100000 \
#   --l3_misses 8000 \
#   --tlb_loads 1200 \
#   --tlb_misses 80 \
#   --branch_instr 700000000 \
#   --branch_misses 50000 \
#   --miss_per_trial 0.0009 \
#   --cycles_per_trial 16.9609
# ```
#
# ## Output:
# - File: logs/batch_<batchid>_<timestamp>/perf_results_<method>_<timestamp>_<batchid>.parquet
# - Format: compressed `zstd` parquet with labeled fields and derived metrics

from pipeline.utils import safe_vector_cast, safe_div_percent
from pipeline.schema import SCHEMA

from pathlib import Path
from glob import glob
import polars as pl
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Parse perf stats for Monte Carlo benchmarking.")
    parser.add_argument("--out_path", required=True, help="Output .parquet file path")
    
    parser.add_argument("--wall_time_s", required=True, help="Wall time (seconds)")
    parser.add_argument("--wall_time_ns", required=True, help="Wall time (nanoseconds)")

    parser.add_argument("--timestamp", required=True, help="Timestamp for the benchmark run")
    parser.add_argument("--batchid", required=True, help="Unique ID for this batch of trials")
    parser.add_argument("--method", required=True, help="Benchmarking method (e.g., SIMD, Pool, etc.)")

    parser.add_argument("--trials", required=True, help="Number of trials run")
    parser.add_argument("--cycles", required=True, help="CPU cycles")
    parser.add_argument("--instr", required=True, help="Instructions executed")
    parser.add_argument("--ipc", required=True, help="Instructions per cycle")

    parser.add_argument("--cache_loads", required=True, help="Cache loads")
    parser.add_argument("--cache_miss", required=True, help="Cache misses")

    parser.add_argument("--l1_loads", required=True, help="L1 data cache loads")
    parser.add_argument("--l1_misses", required=True, help="L1 data cache misses")

    parser.add_argument("--l2_loads", required=True, help="L2 data cache loads")
    parser.add_argument("--l2_misses", required=True, help="L2 data cache misses")

    parser.add_argument("--l3_loads", required=True, help="L3 data cache loads")
    parser.add_argument("--l3_misses", required=True, help="L3 data cache misses")

    parser.add_argument("--tlb_loads", required=True, help="TLB loads")
    parser.add_argument("--tlb_misses", required=True, help="TLB misses")

    parser.add_argument("--branch_instr", required=True, help="Branch instructions")
    parser.add_argument("--branch_misses", required=True, help="Branch misses")

    parser.add_argument("--miss_per_trial", required=True, help="Cache+TLB misses per trial")
    parser.add_argument("--cycles_per_trial", required=True, help="Cycles per trial")
    
    return parser.parse_args()

def update_parquet(args):
    matches = sorted(glob(f"db/logs/batch_{args.batchid}_*"))
    if not matches:
        raise FileNotFoundError(f"No batch directory found for batch ID {args.batchid}")
    batch_dir = Path(matches[-1])

    parquet_path = batch_dir / f"perf_results_{args.method}_{args.timestamp}_{args.batchid}.parquet"

    print("[DEBUG] Wrote parquet to:", parquet_path)

    # 1. Build the raw row (match SCHEMA field names exactly)
    row = {
        "Timestamp": args.timestamp,
        "BatchID": args.batchid,
        "Method": args.method,
        "Trials": args.trials,
        "Cycles": args.cycles,
        "Instructions": args.instr,
        "IPC": args.ipc,
        "Wall Time (s)": args.wall_time_s,
        "Wall Time (ns)": args.wall_time_ns,
        "Cache Loads": args.cache_loads,
        "Cache Misses": args.cache_miss,
        "Cache Miss %": safe_div_percent(args.cache_miss, args.cache_loads),
        "L1 Loads": args.l1_loads,
        "L1 Misses": args.l1_misses,
        "L1 Miss %": safe_div_percent(args.l1_misses, args.l1_loads),
        "L2 Loads": args.l2_loads,
        "L2 Misses": args.l2_misses,
        "L2 Miss %": safe_div_percent(args.l2_misses, args.l2_loads),
        "L3 Loads": args.l3_loads,
        "L3 Misses": args.l3_misses,
        "L3 Miss %": safe_div_percent(args.l3_misses, args.l3_loads),
        "TLB Loads": args.tlb_loads,
        "TLB Misses": args.tlb_misses,
        "TLB Miss %": safe_div_percent(args.tlb_misses, args.tlb_loads),
        "Branch Instructions": args.branch_instr,
        "Branch Misses": args.branch_misses,
        "Branch Miss %": safe_div_percent(args.branch_misses, args.branch_instr),
        "Misses/Trial": args.miss_per_trial,
        "Cycles/Trial": args.cycles_per_trial,
    }

    row = {k: (None if v == "NA" else v) for k, v in row.items()}

    # 2. Create DataFrame and cast using schema
    df = pl.DataFrame([row])

    df = safe_vector_cast(df, SCHEMA)

    df.write_parquet(parquet_path, compression="zstd")

    print(f"[INFO] Parquet saved: {parquet_path}")

if __name__ == "__main__":
    args = parse_args()
    update_parquet(args)
