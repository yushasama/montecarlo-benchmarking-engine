# ===========================================
# schema.py
# ===========================================
#
# @file schema.py
# @brief Defines the canonical schema used across ETL, validation, and ClickHouse ingestion.
#
# Description:
#   This file defines the global SCHEMA dictionary that maps column names to Polars dtypes
#   and nullability flags. It is used for:
#     - Casting CSV inputs via safe_vector_cast()
#     - Enforcing field consistency across benchmarks
#     - Generating ClickHouse CREATE TABLE statements
#
# Format:
#   SCHEMA = {
#       "Column Name": (Polars DataType, is_nullable: bool),
#       ...
#   }
#
# Design Notes:
#   - All timestamps use millisecond-resolution Datetime
#   - Percent fields are stored as Float64 (0–100%)
#   - L2/L3-related fields are nullable by default (may not be available on all CPUs)
#   - Field names match CSV headers and ClickHouse columns exactly


import polars as pl

"""
@brief Canonical schema used throughout the pipeline.

Each key represents a column name, and the value is a tuple:
(dtype: pl.DataType, nullable: bool). This schema is used to:
- Cast raw CSV data safely
- Generate ClickHouse-compatible SQL
- Validate data consistency during preprocessing

@note Nullable fields typically represent optional CPU-level metrics (e.g., L2/L3).
@note Timestamps are expected to be in millisecond resolution.
"""
SCHEMA = {
    # Non-nullable fields
    "Timestamp": (pl.Datetime("ms"), False),
    "BatchID": (pl.Utf8(), False),
    "Method": (pl.Utf8(), False),
    "Trials": (pl.Int64(), False),
    "Cycles": (pl.Int64(), False),
    "Instructions": (pl.Int64(), False),
    "IPC": (pl.Float64(), False),
    "Wall Time (s)": (pl.Float64(), False),
    "Wall Time (ns)": (pl.Int64(), False),
    "Cache Loads": (pl.Int64(), False),
    "Cache Misses": (pl.Int64(), False),
    "Cache Miss %": (pl.Float64(), False),
    "L1 Loads": (pl.Int64(), False),
    "L1 Misses": (pl.Int64(), False),
    "L1 Miss %": (pl.Float64(), False),

    # Nullable fields
    "L2 Loads": (pl.Int64(), True),
    "L2 Misses": (pl.Int64(), True),
    "L2 Miss %": (pl.Float64(), True),
    "L3 Loads": (pl.Int64(), True),
    "L3 Misses": (pl.Int64(), True),
    "L3 Miss %": (pl.Float64(), True),

    "TLB Loads": (pl.Int64(), False),
    "TLB Misses": (pl.Int64(), False),
    "TLB Miss %": (pl.Float64(), False),
    "Branch Instructions": (pl.Int64(), False),
    "Branch Misses": (pl.Int64(), False),
    "Branch Miss %": (pl.Float64(), False),
    "Misses/Trial": (pl.Float64(), False),
    "Cycles/Trial": (pl.Float64(), False),
}