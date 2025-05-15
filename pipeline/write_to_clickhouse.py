from clickhouse_driver import Client
from pipeline.schema import SCHEMA
from pipeline.utils import safe_vector_cast
import argparse
import polars as pl

# --- Parse args ---
parser = argparse.ArgumentParser(description="Insert benchmarking logs into ClickHouse")

parser.add_argument("--batchid", type=str, required=True, help="Batch ID to ingest")

args = parser.parse_args()

parquet_path = "db/db.parquet"

df = pl.read_parquet(parquet_path)

df = df.filter(pl.col("BatchID") == args.batchid)

# --- Connect to ClickHouse ---
client = Client(host="localhost")

# --- Insert ---
records = df.to_dicts()

try:
    client.execute("INSERT INTO benchmark.performance VALUES", records)

except Exception as e:
    print(f"[ERROR] Error inserting records into ClickHouse: {e}")
    raise

print(f"[INFO] Inserted {len(records)} records into ClickHouse.")

