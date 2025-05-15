# ===========================================
# @file parse_perf_csv.py
# @brief CLI flag generator from perf CSV output
# ===========================================
#
# Parses `perf stat -x,` CSV logs and extracts performance metrics,
# outputting them as CLI-ready `--key value` pairs for shell evaluation.
#
# 💡 Output is designed for:
#   eval $(python3 parse_perf_csv.py perf_SIMD.csv)
# → sets: CYCLES=..., INSTR=..., IPC=..., etc.
#
# === Vectorized Extraction (Fast, Clean) ===
#
# Traditional way (slow):
#   for each metric:
#       df.filter(event == name).select("value")  ❌ many scans
#
# Our way (vectorized):
#   - `df.filter(is_in(...))` filters all relevant events in one pass
#   - `<not supported>` is detected via `.str.contains()` and normalized in one go
#   - Results are built using `.iter_rows()` over the filtered subset
#
# ⚙️ Why it's faster:
#   - 1 dataframe scan instead of N
#   - All NA fallback handling done in a single `with_columns()` call
#   - Polars-native ops → no Python loops or string parsing needed
#
# ⚠️ Notes:
#   - L2/L3 events are marked `"NA"` by default unless supported on your CPU
#   - Output order matches expected schema in `gen_perf_parquet_logs.py`
#
# Usage:
#   python3 parse_perf_metrics.py $LOG_PATH TRIALS
#   → prints: --cycles 123456789 --ipc 1.23 ...
#
#   Inside shell script:
#     eval $(python3 "$SCRIPT_DIR/parse_perf_metrics.py" "$LOG_PATH" "$TRIALS")

from pipeline.utils import safe_div
import polars as pl
import sys

trials = int(sys.argv[2])

df = pl.read_csv(sys.argv[1], has_header=False)
df.columns = ["value", "col1", "event", "timestamp", "cpu%", "derived", "label"]

field_map = {
    "cycles": "cycles:u",
    "instr": "instructions:u",
    "cache_loads": "cache-references:u",
    "cache_miss": "cache-misses:u",
    "l1_loads": "L1-dcache-loads:u",
    "l1_misses": "L1-dcache-load-misses:u",
    "l2_loads": "NA",
    "l2_misses": "NA",
    "l3_loads": "NA",
    "l3_misses": "NA",
    "tlb_loads": "dTLB-loads:u",
    "tlb_misses": "dTLB-load-misses:u",
    "branch_instr": "branch-instructions:u",
    "branch_misses": "branch-misses:u",
}

event_to_key = {v: k for k, v in field_map.items() if v != "NA"}
filtered = df.filter(pl.col("event").is_in(event_to_key.keys()))

# Detect non-numeric values (e.g. "<not supported>", "N/A")
to_clean = (
    pl.when(pl.col("value").cast(pl.Float64, strict=False).is_null())
      .then(pl.lit("NA"))
      .otherwise(pl.col("value").cast(pl.Utf8))  # stringify numeric
)

filtered = filtered.with_columns([to_clean.alias("clean_value")])

values = {key: "NA" for key in field_map}

for row in filtered.iter_rows(named=True):
    cli_key = event_to_key[row["event"]]
    values[cli_key] = row["clean_value"]

values["ipc"] = safe_div(values["instr"], values["cycles"])
values["miss_per_trial"] = safe_div(values["cache_miss"], trials)
values["cycles_per_trial"] = safe_div(values["cycles"], trials)

# Ordered output for clean downstream piping
ordered_keys = [
    "cycles", "instr", "ipc",
    "cache_loads", "cache_miss",
    "l1_loads", "l1_misses",
    "l2_loads", "l2_misses",
    "l3_loads", "l3_misses",
    "tlb_loads", "tlb_misses",
    "branch_instr", "branch_misses",
    "miss_per_trial", "cycles_per_trial"
]

# Debugging output
def debug_print(values: dict):
    for k in ordered_keys:
        print(f"[DEBUG] {k} = {values.get(k)}", file=sys.stderr)


print(" ".join([
    f"{k.upper()}={values[k]}"
    for k in ordered_keys
]))