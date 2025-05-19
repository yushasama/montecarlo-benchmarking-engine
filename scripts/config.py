from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

def env(key, default=None):
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