from pipeline.schema import SCHEMA

def polars_to_clickhouse_dtype(dtype, nullable):
    mapping = {
        "Int64": "UInt64",  # or Int64 depending on semantics
        "Float64": "Float32",
        "Utf8": "String",
    }
    dtype_name = dtype.__name__.replace("pl.", "").replace("DataType.", "")
    ch_type = mapping.get(dtype_name, "String")
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

# Example usage
if __name__ == "__main__":
    print(generate_clickhouse_table())