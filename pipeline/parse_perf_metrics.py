# ===========================================
# parse_perf_metrics.py
# ===========================================

## \file parse_perf_metrics.py
## \brief CLI flag generator from perf CSV output (`perf stat -x,`)
##
## \details
## Parses Linux `perf stat` logs in CSV format and extracts a fixed set
## of performance metrics. Outputs these metrics as `--key value` shell
## arguments for downstream use in pipeline scripts or shell evaluation.
##
## Metrics are mapped from perf event names (e.g., `"cycles:u"`) into
## canonical CLI keys (e.g., `CYCLES`, `IPC`). Unsupported metrics are
## filled as `"NA"`. Derived values like IPC and misses per trial are
## computed inline using safe arithmetic fallbacks.
##
## \par Output Format
## \code
## CYCLES=123456789 INSTR=123456 IPC=1.23 ...
## \endcode
## Printed as a single line, space-separated key-value flags, suitable for `eval`.
##
## \par Example
## \code
## $ eval $(python3 parse_perf_metrics.py perf_SIMD.csv 1000000)
## $ echo $CYCLES
## \endcode
##
## \par Usage
## \code
## python3 parse_perf_metrics.py <perf_log.csv> <num_trials>
## \endcode
##
## \par Arguments
## - `<perf_log.csv>` — Path to perf CSV file (from `perf stat -x,`)
## - `<num_trials>` — Number of simulation trials (used for normalization)
##
## \note
## - L2/L3 metrics are set to `"NA"` unless enabled manually via raw PMU events.
## - Designed for use via `eval` in shell pipelines or programmatically via subprocess.
## - Will safely skip unsupported perf fields and calculate derived metrics (e.g., IPC, miss rate).


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