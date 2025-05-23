#!/usr/bin/env python3
# ===========================================
# setup.py
# ===========================================

## \file setup.py
## \brief CLI utility to initialize ClickHouse + Grafana for benchmark pipeline.
##
## \details
## This script handles the full setup flow for the benchmark environment:
## - Starts ClickHouse and Grafana via Docker Compose (optional)
## - Waits for ClickHouse to become ready
## - Creates database and table schema using `schema_to_clickhouse.py`
## - Loads benchmarking data from either:
##   - A sample Parquet file (`samples/db_sample.parquet`)
##   - A user-generated Parquet log (`db/db.parquet`)
##
## \par Usage
## \code
## python3 scripts.setup [--docker-compose] [--setup-clickhouse] [--load-from-sample | --load-from-db]
## \endcode
##
## \par Options
## - `--docker-compose` — Start ClickHouse and Grafana with Docker Compose  
## - `--setup-clickhouse` — Explicitly create the ClickHouse database and performance table  
## - `--load-from-sample` — Load data from `samples/db_sample.parquet` (overwrites DB)  
## - `--load-from-db` — Load data from existing `db/db.parquet` file  
##
## \par Notes
## - Configuration is loaded from `.env` via `scripts/config.py`
## - ClickHouse and Grafana must be available via Docker if `--docker-compose` is used
## - Requires `clickhouse-driver`, `polars`, and Docker CLI to be installed


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
from scripts.config import *


def log(msg: str):
    """!Prints an info message to stdout.

    \param msg The message string.
    \return None
    """
    print(f"[INFO] {msg}")

def err(msg: str):
    """!Prints an error message to stdout.
    @param msg The message string.
    """
    print(f"[ERROR] {msg}")

def run_command(cmd: str):
    """!Executes a shell command with logging.
    @param cmd The command string to run.
    @throws subprocess.CalledProcessError if the command fails.
    """
    log(f"Running command: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def wait_for_clickhouse() -> Client:
    """!Waits for ClickHouse server to become ready, retries for up to 30 attempts.
    @return A connected ClickHouse Client instance.
    @throws RuntimeError if ClickHouse doesn't respond after all attempts.
    """
    log("Waiting for ClickHouse...")

    for attempt in range(30):
        try:
            log(f"Connecting to ClickHouse at {CLICKHOUSE_HOST}:{CLICKHOUSE_TCP_PORT} as user '{CLICKHOUSE_USER}'")
            client = Client(host=CLICKHOUSE_HOST, port=CLICKHOUSE_TCP_PORT, user=CLICKHOUSE_USER, password=CLICKHOUSE_PASSWORD)
            client.execute("SELECT 1")
            log("ClickHouse is ready.")
            return client
        
        except Exception as e:
            log(f"Attempt {attempt+1}/30 failed: {e}")
            time.sleep(2)

    raise RuntimeError("ClickHouse did not start after 30 attempts.")

def setup_clickhouse(client: Client):
    """!Creates the ClickHouse database and performance table if they don't exist.
    @param client The connected ClickHouse client.
    """
    log("Setting up ClickHouse database and table.")
    client.execute("CREATE DATABASE IF NOT EXISTS benchmark")
    client.execute(generate_clickhouse_table())
    log("Schema loaded into ClickHouse.")

def load_db_to_clickhouse(client: Client, db_path: Path):
    """!Wipes previous data and loads data from a Parquet file into ClickHouse.

    Casts data using the shared schema and inserts it into the benchmark.performance table.
    Existing table data will be truncated.

    @param client The connected ClickHouse client.
    @param db_path Path to the Parquet file to load.
    @throws FileNotFoundError if the file does not exist.
    @throws Exception if insertion fails.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"{db_path} not found")

    log(f"Loading data from: {db_path}")
    df = pl.read_parquet(db_path)
    df = safe_vector_cast(df, SCHEMA)

    records = df.to_dicts()
    
    if not records:
        log("No records to insert.")
        return
    
    try:
        client.execute("TRUNCATE TABLE benchmark.performance")
        client.execute("INSERT INTO benchmark.performance VALUES", records)
    except Exception as e:
        err(f"Error inserting records into ClickHouse: {e}")
        raise
    

def main():
    """!CLI entrypoint. Parses arguments and coordinates Docker, schema setup, and data loading.
    """
    parser = argparse.ArgumentParser(description="Setup and load benchmark data into ClickHouse")
    parser.add_argument("--load-from-sample", action="store_true", help="Setup and restore from db_sample.parquet")
    parser.add_argument("--load-from-db", action="store_true", help="Setup and use existing db.parquet")
    parser.add_argument("--docker-compose", action="store_true", help="Use Docker Compose to start ClickHouse & Grafana")
    parser.add_argument("--setup-clickhouse", action="store_true", help="Setup ClickHouse database and table")

    args = parser.parse_args()

    os.makedirs("db", exist_ok=True)
    os.makedirs("samples", exist_ok=True)
    os.makedirs("db/logs", exist_ok=True)

    if args.docker_compose:
        log("Setting up docker instance to be ready for ClickHouse database and Grafana.")
        run_command("docker-compose up -d")
        time.sleep(5)  # Wait for ClickHouse to start

    client = wait_for_clickhouse()

    if args.setup_clickhouse or args.docker_compose:
        setup_clickhouse(client)

    if args.load_from_sample or args.load_from_db:
        ## Create the database and table if they don't exist
        log("Creating database and table if they don't exist.")
        client.execute("CREATE DATABASE IF NOT EXISTS benchmark")
        client.execute(generate_clickhouse_table())
        
    if args.load_from_sample:
        log(f"Loading from sample data: {SAMPLE_PATH}")
        shutil.copy(SAMPLE_PATH, DB_PATH)
        load_db_to_clickhouse(client, DB_PATH)

    elif args.load_from_db:
        log(f"Loading from existing data: {DB_PATH}")
        load_db_to_clickhouse(client, DB_PATH)

    if args.load_from_sample or args.load_from_db:
        run_command("docker restart grafana")


if __name__ == "__main__":
    main()