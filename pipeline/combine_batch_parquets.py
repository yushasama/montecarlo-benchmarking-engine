# ===========================================
# combine_batch_parquets.py
# ===========================================
#
# @file combine_batch_parquets.py
# @brief Combines multiple per-method parquet log files into a single file.
#
# Description:
#   Scans a given batch directory for all `perf_results_*.parquet` files,
#   excluding the output file itself. Merges them using vertical concat,
#   sorts by "Timestamp", and saves the result as a single compressed parquet.
#
#   After merging, the result is also appended to a global historical
#   file specified by `DB_PATH`, which is configured via `.env` and loaded
#   in `scripts/config.py`.
#
# Compression:
#   - All output parquet files are compressed using Zstandard (zstd).
#
# Usage:
#   $ python3 combine_batch_parquets.py <batch_dir> <output_file>
#
# Arguments:
#   <batch_dir>     Folder containing individual `.parquet` logs
#   <output_file>   Path to final combined `.parquet` file
#
# Output:
#   - A merged parquet file containing all batch results
#   - Updated global Parquet DB with new rows appended
#
# Notes:
#   - Global Parquet path is loaded from `.env` via `scripts/config.py`
#   - This script uses `polars` for fast DataFrame operations and I/O
#   - Intended to be run after `run_perf.sh` completes all method benchmarks


from scripts.config import DB_PATH
from pathlib import Path
import polars as pl
import sys

if len(sys.argv) != 3:
    print("Usage: combine_batch_parquets.py <batch_dir> <output_file>")
    sys.exit(1)

batch_dir = Path(sys.argv[1])
output_path = Path(sys.argv[2])
global_db_path = Path(DB_PATH)

# --- 1. Combine batch parquet files ---
files = [f for f in batch_dir.glob("perf_results_*.parquet") if f.name != output_path.name]
if not files:
    print(f"[ERROR] No .parquet files found in {batch_dir}")
    sys.exit(0)

merged = pl.concat([pl.read_parquet(f) for f in files], how="vertical_relaxed").sort("Timestamp")
merged.write_parquet(output_path, compression="zstd")
print(f"[INFO] Merged batch saved: {output_path}")


# --- 2. Append to global db.parquet ---
if global_db_path.exists():
    db = pl.read_parquet(global_db_path)
    db = pl.concat([db, merged], how="vertical_relaxed")
    print("[INFO] Appended to existing db.parquet")
else:
    db = merged
    print("[INFO] Created new db.parquet")

db.write_parquet(global_db_path, compression="zstd")
print(f"[INFO] Parquet db updated: {global_db_path}")