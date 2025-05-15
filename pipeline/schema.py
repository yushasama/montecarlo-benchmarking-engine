import polars as pl

SCHEMA = {
    "Trials": (pl.Int64, False),
    "Cycles": (pl.Int64, False),
    "Instructions": (pl.Int64, False),
    "IPC": (pl.Float64, False),
    "Wall Time (s)": (pl.Float64, False),
    "Wall Time (ns)": (pl.Int64, False),
    "Cache Loads": (pl.Int64, False),
    "Cache Misses": (pl.Int64, False),
    "Cache Miss %": (pl.Float64, False),
    "L1 Loads": (pl.Int64, False),
    "L1 Misses": (pl.Int64, False),
    "L1 Miss %": (pl.Float64, False),

    # Nullable fields
    "L2 Loads": (pl.Int64, True),
    "L2 Misses": (pl.Int64, True),
    "L2 Miss %": (pl.Float64, True),
    "L3 Loads": (pl.Int64, True),
    "L3 Misses": (pl.Int64, True),
    "L3 Miss %": (pl.Float64, True),

    
    "TLB Loads": (pl.Int64, False),
    "TLB Misses": (pl.Int64, False),
    "TLB Miss %": (pl.Float64, False),
    "Branch Instructions": (pl.Int64, False),
    "Branch Misses": (pl.Int64, False),
    "Branch Miss %": (pl.Float64, False),
    "Misses/Trial": (pl.Float64, False),
    "Cycles/Trial": (pl.Float64, False),
}
