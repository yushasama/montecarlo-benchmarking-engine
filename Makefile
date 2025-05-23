# ===========================================
# Makefile — Monte Carlo Benchmarking Engine
# ===========================================
#
# DevOps interface for local simulation and analytics stack.
# Manages ClickHouse, Grafana, and related data pipelines.
# ===========================================

# Print help for all available commands
help:  ## Show available commands
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?##' Makefile | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'

# Start all containers without rebuilding
start:  ## Start Docker containers
	docker-compose up -d

# Stop all containers but preserve data volumes
stop:  ## Stop containers, preserve volumes
	docker-compose down

# Restart containers with a fresh build, preserving volume data
rebuild:  ## Rebuild containers without deleting data
	docker-compose down
	docker-compose up -d --build

# Full reset: remove containers, delete all volumes, rebuild from scratch
reset_all:  ## Wipe containers and volumes, rebuild from clean state
	docker-compose down -v
	docker volume rm montecarlo-benchmarking-engine_clickhouse-data || true
	docker volume rm montecarlo-benchmarking-engine_grafana-storage
	docker-compose build --no-cache
	make fix_clickhouse_ownership
	docker-compose up -d

# Dangerous: Remove *everything* (volumes, local files, Docker system state)
clean_all:  ## Full system purge including local files (requires sudo)
	@if [ "$$(id -u)" -ne 0 ]; then \
		echo "Must run with sudo. Aborting."; \
		exit 1; \
	fi
	docker-compose down -v
	docker volume prune -f
	docker system prune -af --volumes
	rm -rf db/*

# Remove only local Parquet data from simulation
clear_data:  ## Clear local data folder (safe)
	rm -rf db/*

# Tail logs from all running containers
logs:  ## Stream logs from containers
	docker-compose logs -f

# Remove all Parquet logs from the repo
clear_parquets:  ## Delete all local .parquet files
	find . -name "*.parquet" -delete

# Initialize from scratch: build containers and setup ClickHouse schema
init:  ## Initialize containers and ClickHouse schema
	python3 -m scripts.setup --docker-compose

# Initialize with sample data for visual demos
init_demo:  ## Initialize with preloaded sample data
	python3 -m scripts.setup --docker-compose --load-from-sample

# Load existing db.parquet into ClickHouse
load_data:  ## Load production data into ClickHouse
	python3 -m scripts.setup --load-from-db

# Load sample parquet file (offline demo mode)
load_demo:  ## Load demo data from bundled .parquet
	python3 -m scripts.setup --load-from-sample

# Manually recreate ClickHouse schema
setup_clickhouse:  ## Force schema creation in ClickHouse
	python3 -m scripts.setup --setup-clickhouse

# Reset only Grafana credentials (without touching other data)
reset_grafana_creds:  ## Delete Grafana volume to reset credentials
	docker-compose stop grafana
	docker volume rm montecarlo-benchmarking-engine_grafana-storage
	docker-compose up -d grafana

# Fix UID mismatch to prevent ClickHouse crash (Exit Code 174)
fix_clickhouse_ownership:  ## Reset ClickHouse volume ownership to uid/gid 101
	@echo "[INFO] Resetting ClickHouse volume ownership to match container expectations..."
	docker run --rm \
	  -v montecarlo-benchmarking-engine_clickhouse-data:/data \
	  alpine sh -c "addgroup -g 101 clickhouse && adduser -D -u 101 -G clickhouse clickhouse && chown -R clickhouse:clickhouse /data"
	@echo "[INFO] Ownership reset to clickhouse:clickhouse (uid/gid 101)."