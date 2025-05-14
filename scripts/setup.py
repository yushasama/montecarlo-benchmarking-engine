#!/usr/bin/env python3
import argparse
import subprocess
import os
import shutil
import time
from pathlib import Path
from clickhouse_driver import Client
import polars as pl

from pipeline.schema_to_clickhouse import generate_clickhouse_table
from pipeline.schema import SCHEMA
from pipeline.utils import safe_vector_cast

DB_PATH = Path("db/db.parquet")
SAMPLE_PATH = Path("samples/db_sample.parquet")


def log(msg: str):
    print(f"[INFO] {msg}")

def err(msg: str):
    print(f"[ERROR] {msg}")

def run_command(cmd: str):
    log(f"Running command: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def wait_for_clickhouse():
    log("Waiting for ClickHouse...")
    for attempt in range(30):
        try:
            client = Client(host="localhost", port=9000, user="default")
            client.execute("SELECT 1")
            log("ClickHouse is ready.")
            return client
        except Exception as e:
            log(f"Attempt {attempt+1}/30 failed: {e}")
            time.sleep(2)
    raise RuntimeError("ClickHouse did not start after 30 attempts.")

def setup_clickhouse(client: Client):
    log("Setting up ClickHouse database and table.")
    client.execute("CREATE DATABASE IF NOT EXISTS benchmark")
    client.execute(generate_clickhouse_table())
    log("Schema loaded into ClickHouse.")

def load_db_to_clickhouse(client: Client, db_path: Path):
    if not db_path.exists():
        raise FileNotFoundError(f"{db_path} not found")

    log(f"Loading data from: {db_path}")
    df = pl.read_parquet(db_path)
    df = safe_vector_cast(df, SCHEMA)

    records = df.to_pandas().to_dict(orient="records")
    if not records:
        log("No records to insert.")
        return

    client.execute("INSERT INTO benchmark.performance VALUES", records)
    log(f"Inserted {len(records)} records into ClickHouse.")

def main():
    parser = argparse.ArgumentParser(description="Setup and load benchmark data into ClickHouse")
    parser.add_argument("--load-from-sample", action="store_true", help="Restore from db_sample.parquet")
    parser.add_argument("--load-from-db", action="store_true", help="Use existing db.parquet")
    args = parser.parse_args()

    os.makedirs("db", exist_ok=True)
    os.makedirs("samples", exist_ok=True)
    os.makedirs("db/logs", exist_ok=True)

    run_command("docker-compose up -d")
    client = wait_for_clickhouse()
    setup_clickhouse(client)

    if args.load_from_sample:
        log("Restoring from sample parquet file.")
        shutil.copy(SAMPLE_PATH, DB_PATH)
        load_db_to_clickhouse(client, DB_PATH)

    elif args.load_from_db:
        log("Using existing db.parquet.")
        load_db_to_clickhouse(client, DB_PATH)

    else:
        err("No load option provided. Use --load-from-sample or --load-from-db.")
        log("Example: python3 -m scripts.setup --load-from-sample")

if __name__ == "__main__":
    main()
