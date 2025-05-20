# ===========================================
# Makefile — Monte Carlo Benchmarking Engine
# ===========================================
#
# Friendly DevOps commands for local simulation + ClickHouse stack.
# Includes clean naming, safe init flows, and soft resets.
#

# 🐳 Start the Docker containers (no rebuild)
start:
	docker-compose up -d

# 📦 Stop containers, keep data
stop:
	docker-compose down

# 🔄 Restart + rebuild images (preserves all data)
rebuild:
	docker-compose down
	docker-compose up -d --build

# 🧼 Restart from scratch (deletes volumes, rebuilds everything)
reset_all:
	docker-compose down -v
	docker-compose up -d --build

# 🧹 Clean everything: Docker volumes + local data (Careful!)
clean_all:
	docker-compose down -v
	rm -rf db/*
	rm -rf clickhouse_data/*
	rm -rf grafana/data/*

# 📁 Just delete local simulation data (safe)
clear_data:
	rm -rf db/*

# 📜 Stream logs from all containers
logs:
	docker-compose logs -f

# 🧽 Delete all local .parquet logs
clear_parquets:
	find . -name "*.parquet" -delete

# 🌱 Full environment init:
# - Starts Docker stack
# - Sets up ClickHouse DB & schema
init:
	python3 -m scripts.setup --docker-compose

# 🌸 Init with sample data (for demos, blog screenshots)
init_demo:
	python3 -m scripts.setup --docker-compose --load-from-sample

# 📥 Load existing db.parquet into ClickHouse
load_data:
	python3 -m scripts.setup --load-from-db

# 🧺 Load sample parquet (for offline demo mode — copies db_sample.parquet into db/db.parquet)
load_demo:
	python3 -m scripts.setup --load-from-sample

# 🛠️ Manually reinitialize ClickHouse DB + schema
setup_clickhouse:
	python3 -m scripts.setup --setup-clickhouse

