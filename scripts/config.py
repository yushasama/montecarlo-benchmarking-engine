# ===========================================
# config.py
# ===========================================

## \file config.py
## \brief Loads environment-based configuration for pipeline and services.
## 
## \par Description
##     Central configuration module that reads environment variables via `dotenv`
##     and exposes all necessary settings for:
##     - ClickHouse connections
##     - Local and Docker-based port mapping
##     - Global Parquet file paths for pipeline storage
##     
##     This module wraps `os.getenv()` via the `env()` helper, enabling
##     fallback defaults and central management of required keys.
## 
## \par Usage
##     from scripts.config import CLICKHOUSE_HOST, DB_PATH, ...
##     Parquet writers/readers will use `DB_PATH` and `SAMPLE_PATH`.
##     CLI runners and ingestion tools will use ClickHouse config values.
## 
## \par Notes
##     - Loads from `.env` file in the project root (via `python-dotenv`)
##     - All paths are converted into `Path()` objects for consistency
##     - Ports are cast to `int` to prevent runtime casting bugs


from dotenv import load_dotenv
from pathlib import Path
import os


load_dotenv()

def env(key, default=None):
    """!Retrieve an environment variable with an optional default.

    @param key The environment variable key to read.
    @param default The fallback value to use if the variable is not set.

    @return The environment value as a string, or the default if not found.
    """
    return os.getenv(key, default)

CLICKHOUSE_HOST = env("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_TCP_PORT = int(env("CLICKHOUSE_TCP_PORT", 9000))
CLICKHOUSE_HTTP_PORT = int(env("CLICKHOUSE_HTTP_PORT", 8123))
CLICKHOUSE_USER = env("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = env("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_HOST_DOCKER = env("CLICKHOUSE_HOST_DOCKER", "clickhouse")
CLICKHOUSE_TCP_PORT_DOCKER = int(env("CLICKHOUSE_TCP_PORT_DOCKER", 9000))
CLICKHOUSE_HTTP_PORT_DOCKER = int(env("CLICKHOUSE_HTTP_PORT_DOCKER", 8123))
load_dotenv()

DB_PATH = Path(env("DB_PATH", "db/db.parquet"))
SAMPLE_PATH = Path(env("SAMPLE_PATH", "samples/db_sample.parquet"))