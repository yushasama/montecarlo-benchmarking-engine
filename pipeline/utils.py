from pipeline.schema import SCHEMA
from polars import col, when
import polars as pl

def safe_vector_cast(df: pl.DataFrame, schema: dict) -> pl.DataFrame:
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
    try:
        if "NA" in (numerator, denominator):
            return "NA"
        
        num = float(numerator)
        denom = float(denominator)

        return round(num / denom, 4)
    except:
        return "NA"

def safe_div_percent(numerator, denominator):
    try:
        if "NA" in (numerator, denominator):
            return "NA"
        
        num = float(numerator)
        denom = float(denominator)

        return round((num / denom) * 100, 4)
    except:
        return "NA"
