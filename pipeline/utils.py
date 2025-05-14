from polars import col, when
import polars as pl

def safe_vector_cast(df: pl.DataFrame, schema: dict) -> pl.DataFrame:
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

    return df.with_columns([
        (
            when(col(c) == "NA").then(None).otherwise(col(c)).cast(t).alias(c)
            if allow_na else col(c).cast(t).alias(c)
        )
        for c, (t, allow_na) in schema.items()
    ])
