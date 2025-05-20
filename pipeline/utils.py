# ===========================================
# utils.py
# ===========================================
#
# @file utils.py
# @brief Shared utilities for safe casting, schema enforcement, and arithmetic fallback logic.
#
# Description:
#   This module provides shared helpers for safely working with metrics data in a
#   Polars-based pipeline. It ensures robust schema alignment and safe numerical operations,
#   especially when working with mixed or incomplete CSV inputs.
#
# Included Utilities:
#   - safe_vector_cast:    Vectorized, schema-aware casting for Polars DataFrames
#   - safe_div:            Division with fallback for invalid or "NA" input
#   - safe_div_percent:    Percentage-style division with "NA" guard
#
# Usage:
#   from utils import safe_vector_cast, safe_div, safe_div_percent
#
# Design Notes:
#   - Schema mismatches are surfaced with detailed debug output
#   - "NA" strings are treated as nulls when allow_na is True
#   - Division errors (e.g., zero division, bad input) are handled gracefully
#

from pipeline.schema import SCHEMA
from polars import col, when
import polars as pl

def safe_vector_cast(df: pl.DataFrame, schema: dict) -> pl.DataFrame:
    """
    @brief Cast a Polars DataFrame to match a declared schema, handling 'NA' strings as nulls.

    This function enforces schema alignment between a raw input DataFrame (typically from CSV)
    and a declared schema. If `allow_na` is True in the schema, string values like "NA" will be
    replaced with nulls prior to casting.

    @param df The input Polars DataFrame to cast.
    @param schema Dictionary in the format { column_name: (dtype, allow_na) }.

    @return A new Polars DataFrame with all fields casted according to the schema.

    @throws ValueError If any schema field is missing in the DataFrame.
    """
    try:
        missing = [c for c in schema if c not in df.columns]

        if missing:
            print("SCHEMA MISMATCH DETECTED")
            print("Expected columns (from schema):")
            for s in schema:
                print(f"  {s}")
            print("Found columns (in DataFrame):")
            for c in df.columns:
                print(f"  {c}")
            print("Missing columns:")
            for m in missing:
                print(f"  {m}")
            raise ValueError(f"Schema mismatch: {len(missing)} missing column(s)")

        casted = []

        for c, (dtype, allow_na) in schema.items():
            if allow_na and df[c].dtype == pl.Utf8:
                expr = when(col(c) == "NA").then(None).otherwise(col(c)).cast(dtype).alias(c)
            else:
                expr = col(c).cast(dtype).alias(c)
            casted.append(expr)

        return df.with_columns(casted)
    
    except Exception as e:
        print("[ERROR] safe_vector_cast failed:", e)
        print("[DEBUG] DataFrame columns:", df.columns)
        print("[DEBUG] Schema fields:", list(SCHEMA.keys()))
        raise e

def safe_div(numerator, denominator):
    """
    @brief Safely performs division, handling 'NA' values and invalid input.

    Returns a rounded division result unless input is invalid or contains the string "NA",
    in which case "NA" is returned instead.

    @param numerator Numerator of the division (can be int, float, or "NA").
    @param denominator Denominator of the division (can be int, float, or "NA").

    @return Result of division rounded to 4 decimal places, or "NA" if invalid.
    """
    try:
        if "NA" in (numerator, denominator):
            return "NA"
        
        num = float(numerator)
        denom = float(denominator)

        return round(num / denom, 4)
    except:
        return "NA"

def safe_div_percent(numerator, denominator):
    """
    @brief Computes percentage-based division safely, with 'NA' fallback.

    Similar to safe_div, but multiplies the result by 100 to express it as a percent.
    Invalid input or "NA" strings will return "NA" as a string.

    @param numerator Numerator of the division (can be int, float, or "NA").
    @param denominator Denominator of the division (can be int, float, or "NA").

    @return Percentage value (rounded to 4 decimals), or "NA" if invalid.
    """
    try:
        if "NA" in (numerator, denominator):
            return "NA"
        
        num = float(numerator)
        denom = float(denominator)

        return round((num / denom) * 100, 4)
    except:
        return "NA"
