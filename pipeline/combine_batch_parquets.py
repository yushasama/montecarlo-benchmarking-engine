# ===========================================
# combine_batch_parquets.py
# ===========================================
##
# @file combine_batch_parquets.py
# @brief Combines multiple per-method parquet log files into a single file.
#
# Scans a given batch directory for all `perf_results_*.parquet` files,
# excluding the target output file itself. Merges them into a single parquet
# using vertical concat and sorts by "Timestamp".
#
# Compression: zstd
#
# ## Usage:
# ```bash
# python3 combine_batch_parquets.py <batch_dir> <output_file>
# ```
#
# ## Arguments:
# - `<batch_dir>`: Folder containing individual `.parquet` logs
# - `<output_file>`: Path to final combined `.parquet` file
#
# ## Output:
# - A single merged parquet file
# - Logs warning if no files are found in the batch directory

from pathlib import Path
import polars as pl
import sys

if len(sys.argv) != 3:
    print("Usage: combine_batch_parquets.py <batch_dir> <output_file>")
    sys.exit(1)

batch_dir = Path(sys.argv[1])
output_path = Path(sys.argv[2])
global_db_path = Path("db/db.parquet")

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