import argparse
import polars as pl
from clickhouse_driver import Client

# --- Parse args ---
parser = argparse.ArgumentParser(description="Insert benchmarking logs into ClickHouse")

parser.add_argument("--batchid", type=str, required=True, help="Batch ID to ingest")
parser.add_argument('--demo', action='store_true', help='Use demo parquet (samples/db_sample.parquet)')

args = parser.parse_args()

# --- Choose source file ---
if args.demo:
    parquet_path = "samples/db_sample.parquet"
    print("Using sample data: samples/db_sample.parquet")
else:
    parquet_path = "db/db.parquet"
    print("Using stored data: db/db.parquet")

# --- Load data ---
df = pl.read_parquet(parquet_path)

# --- Filter only target batch ---
df = df.filter(pl.col("BatchID") == args.batchid)

# --- Fix 'NA' strings → None ---
df = df.with_columns([
    pl.when(pl.col(col) == "NA")
      .then(None)
      .otherwise(pl.col(col))
      .alias(col)
    for col in df.columns if df[col].dtype == pl.Utf8
])

records = df.to_pandas().to_dict(orient="records")

# --- Print record names ---
print(f"[DEBUG] Record names for batch {args.batchid}:\n{list(records[0].keys())}")

if not records:
    raise ValueError(f"No records found for batch {args.batchid}")

# 🔍 Debug keys
print(f"[DEBUG] First record keys:\n{list(records[0].keys())}")

# --- Connect to ClickHouse ---
client = Client(host="localhost")

# --- Insert ---
print(f"Inserting {len(records)} records into ClickHouse...")
client.execute("INSERT INTO benchmark.performance VALUES", records)
print("Insert complete")