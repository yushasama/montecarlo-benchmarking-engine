# ===== Monte Carlo Benchmarking Engine Makefile =====

# 🐳 Bring up Docker stack (no rebuild)
up:
	docker-compose up -d

# 💥 Tear down containers (volumes not deleted)
down:
	docker-compose down

# 🔁 Full restart with image rebuild (no data loss)
rebuild:
	docker-compose down
	docker-compose up -d --build

# 🧨 Full restart and delete volumes
nuke_docker:
	docker-compose down -v
	docker-compose up -d --build

nuke_all:
	docker-compose down -v
	docker-compose up -d --build
	rm -rf db/*

nuke_data:
	rm -rf db/*

# 📜 Tail live logs from all containers
logs:
	docker-compose logs -f

# 🧼 Clean all Parquet files
clean:
	find . -name "*.parquet" -delete

# 🚀 Full environment init:
# - Start Docker
# - Setup ClickHouse DB + table

init:
	python3 -m scripts.setup --docker-compose

init_demo:
	python3 -m scripts.setup --docker-compose --load-from-sample

load_only:
	python3 -m scripts.setup --load-from-db

load_only_demo:
	python3 -m scripts.setup --load-from-sample

setup_clickhouse:
	python3 -m scripts.setup --setup-clickhouse