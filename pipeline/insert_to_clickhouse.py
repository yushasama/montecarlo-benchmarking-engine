# ===========================================
# insert_to_clickhouse.py
# ===========================================
#
# @file insert_clickhouse.py
# @brief Inserts filtered benchmarking logs into a ClickHouse database.
#
# Description:
#   This script reads a Parquet dataset, filters it by BatchID, and inserts
#   the matching records into the `benchmark.performance` table in ClickHouse.
#   It uses the clickhouse-driver to perform inserts and ensures that the
#   table schema matches the format defined in `pipeline.schema`.
#
# Usage:
#   $ python3 insert_to_clickhouse.py --batchid <BATCH_ID>
#
# Example:
#   $ python3 insert_to_clickhouse.py --batchid "batch_202405"
#
# Notes:
#   - ClickHouse connection parameters are loaded from `.env`via `scripts/config.py`
#   - The Parquet file path is set in `DB_PATH`
#   - You may call `insert_batch(batch_id)` directly from other scripts or notebooks
#

import argparse
import polars as pl
from clickhouse_driver import Client
from pipeline.schema import SCHEMA
from pipeline.utils import safe_vector_cast
from scripts.config import *


def insert_batch(batch_id: str) -> None:
    """
    @brief Filters and inserts a batch of records into ClickHouse.

    Loads data from the Parquet file at DB_PATH, filters by BatchID,
    and inserts the resulting records into the `benchmark.performance` table.

    @param batch_id The BatchID to filter the dataset on.

    @throws Exception If ClickHouse insert fails.
    """
    df = pl.read_parquet(DB_PATH)
    df = df.filter(pl.col("BatchID") == batch_id)

    # Optional: enforce schema casting
    df = safe_vector_cast(df, SCHEMA)

    client = Client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_TCP_PORT,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD
    )

    records = df.to_dicts()

    try:
        client.execute("INSERT INTO benchmark.performance VALUES", records)
    except Exception as e:
        print(f"[ERROR] Error inserting records into ClickHouse: {e}")
        raise

    print(f"[INFO] Inserted {len(records)} records into ClickHouse for batch '{batch_id}'.")


def main():
    """
    @brief CLI entrypoint for inserting a batch into ClickHouse.

    Parses --batchid from command-line arguments and performs the insert.
    """
    parser = argparse.ArgumentParser(description="Insert benchmarking logs into ClickHouse")
    parser.add_argument("--batchid", type=str, required=True, help="Batch ID to ingest")
    args = parser.parse_args()

    insert_batch(args.batchid)


if __name__ == "__main__":
    main()
