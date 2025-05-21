# ===========================================
# schema_to_clickhouse.py
# ===========================================

## \file schema_to_clickhouse.py
## \brief Converts Polars schema to ClickHouse-compatible SQL
##
## \details
## Converts a shared Python/Polars schema definition into a ClickHouse-compatible
## CREATE TABLE statement. This allows seamless integration between data preprocessing
## with Polars and persistent storage in ClickHouse.
##
## The schema is defined as a dictionary mapping field names to (dtype, nullable) pairs.
## Supported input dtypes include both string representations (e.g., "Utf8") and
## Polars type objects or classes (e.g., pl.Int64).
##
## \par Example Output
## \code
## CREATE TABLE IF NOT EXISTS benchmark.performance (
##     `Method` String,
##     `Cycles` Int64,
##     `IPC` Float64,
##     ...
## ) ENGINE = MergeTree()
## ORDER BY (Method, Timestamp);
## \endcode
##
## \par Features
## - Handles both string-based and Polars-native dtype declarations
## - Adds Nullable(...) wrappers where needed
## - Raises errors for unsupported or unrecognized dtypes
## - Keeps output consistent with the expected schema in `pipeline.schema`
##
## \par Usage
## \code
## $ python3 schema_to_clickhouse.py
## → prints CREATE TABLE SQL for use in ClickHouse CLI
## \endcode
##
## \par Expected Schema Format
## \code{.py}
## SCHEMA = {
##     "FieldName": (pl.Int64, False),
##     "OtherField": ("Utf8", True),
##     ...
## }
## \endcode

from pipeline.schema import SCHEMA
import polars as pl

def polars_to_clickhouse_dtype(dtype, nullable):
    """!Converts a Polars data type to a valid ClickHouse column type.

    This function normalizes the input dtype, whether it's a string (e.g., "Utf8"),
    a Polars dtype class (e.g., pl.Int64), or an instantiated Polars dtype.

    @param dtype The input data type (string, Polars class, or Polars dtype object).
    @param nullable Whether to wrap the type in ClickHouse's Nullable().

    @return A string representing the ClickHouse-compatible column type.

    @throws ValueError If the dtype is not supported or recognized.
    """
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
    """!Generates a CREATE TABLE SQL statement for ClickHouse.

    Converts the SCHEMA dictionary into a fully-typed ClickHouse DDL statement.
    Each field is converted using polars_to_clickhouse_dtype().

    @param table_name The name of the target ClickHouse table.

    @return A multi-line SQL string to define the table in ClickHouse.

    @note Uses MergeTree engine and orders by (Method, Timestamp).
    """
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