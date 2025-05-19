from pipeline.schema import SCHEMA
import polars as pl

def polars_to_clickhouse_dtype(dtype, nullable):
    # Step 1: Normalize if it's a string
    if isinstance(dtype, str):
        dtype_map = {
            "String": "String",
            "Utf8": "String",
            "Int64": "Int64",
            "Float64": "Float64",
            "Datetime": "DateTime64(3)",
        }
        ch_type = dtype_map.get(dtype)
        if ch_type is None:
            raise ValueError(f"Unsupported string dtype: {dtype}")
        return f"Nullable({ch_type})" if nullable else ch_type

    # Step 2: If it's a Polars dtype object or class
    if isinstance(dtype, type):
        dtype = dtype()

    dtype_name = type(dtype).__name__

    match dtype_name:
        case "Utf8" | "String": ch_type = "String"
        case "Int64": ch_type = "Int64"
        case "Float64": ch_type = "Float64"
        case "Datetime": ch_type = "DateTime64(3)"
        case _: raise ValueError(f"Unsupported dtype: {dtype_name}")

    return f"Nullable({ch_type})" if nullable else ch_type

def generate_clickhouse_table(table_name="benchmark.performance"):
    lines = []

    for name, (dtype, nullable) in SCHEMA.items():
        ch_type = polars_to_clickhouse_dtype(dtype, nullable)
        lines.append(f"    `{name}` {ch_type},")

    return f"""CREATE TABLE IF NOT EXISTS {table_name} (
{chr(10).join(lines).rstrip(',')}
) ENGINE = MergeTree()
ORDER BY (Method, Timestamp);"""

if __name__ == "__main__":
    print(generate_clickhouse_table())