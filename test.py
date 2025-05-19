import polars as pl


path = "samples/perf_results_Heap_2025-05-13_17-47-40_c6d4dcc6.parquet"

df = pl.read_parquet(path)

df = df.with_columns([
    pl.col("Timestamp").str.strptime(pl.Datetime("ms"), "%Y-%m-%d %H:%M:%S")
])

df.write_parquet(path, compression="zstd")