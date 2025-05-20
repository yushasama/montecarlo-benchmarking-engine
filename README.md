# Monte Carlo Benchmark Engine

[![CI](https://github.com/yushasama/montecarlo-benchmarking-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/yushasama/montecarlo-benchmarking-engine/actions)

A high-performance SIMD Monte Carlo engine to estimate PI. written in C++17, benchmarked via `perf` and validated via CI. Engine is built to be highly optimized through SIMD aware programming (AVX2 / Neon), multi-threading, custom bump allocator, and cache-aligned memory strategies, bitmasking.

Benchmarked using an in-house `perf` suite, and tested via CI.

> 🔬 Originally based on a Spring 2025 CSULB CECS 325 (Systems Programming) assignment by Neal Terrell. Highly extended and tuned by Leon - just for fun.

> π is estimated by randomly sampling (x, y) points in a unit square and counting how many fall inside the unit circle — the ratio approximates π/4. Which is then multiplied by 4 to get our approximation of π.

---

→ [View Online Documentation](https://yushasama.github.io/montecarlo-benchmarking-engine/)

---

## 📚 Table of Contents

1. [Features](#-features)
2. [Core Optimization Strategies](#-optimization-strategies)
   * [Distance Check Formula](#1-distance-check-formula)
   * [SIMD](#2-simd-accelerated-trial-execution)
   * [Bitmasking](#3-bitmasking-fast-hit-counting-with-no-branches)
   * [Memory Pool Allocator](#4-memory-optimization-pool-allocator)
   * [Thread-Local Design](#5-thread-local-everything-no-locks)
3. [Real-World Analogy: HFT](#real-world-analogy-high-frequency-trading-hft)
4. [Benchmark-Oriented Design Summary](#benchmark-oriented-design-summary)
5. [Tips for Reviewers / Recruiters](#-tip-for-reviewers--recruiters)
6. [Requirements](#requirements)
7. [Setup Instructions](#setup-instructions)

   * [Arch Linux](#-arch-linux)
   * [Linux](#-linux)
   * [macOS](#-macos-with-homebrew)
   * [Windows (WSL2)](#-windows-wsl2--recommended)
   * [Windows (MSVC)](#️-windows-msvc--experimental)
8. [Building & Running](#building--running)
9. [Benchmark Suite (Optional)](#-running-benchmark-suite-optional)
10. [Docker + Grafana Integration](#-docker-optional-for-clickhouse--grafana-setup--data-visualization)
11. [Perf Dashboard Setup (Docker + Makefile)](#️-perf-dashboard-setup-docker--makefile)
12. [Environment Configuration](#-environment-configuration-env)
13. [GitHub Actions CI](#-github-actions-ci)
14. [Sample Benchmark Logs](#-performance-benchmark-snapshot)

---

## 🧩 Features

* **Execution Models**:

  * Sequential
  * Heap-allocated w/ multi threading
  * Custom bump memory pool allocator (thread-local, reset-based) w/ multi threading
  * SIMD-accelerated (AVX2 / NEON) w/ memory pool & multi threading

* **Memory Optimization**:

  * Preallocated, thread-local memory pools for allocation-free reuse
  * Structure-of-Arrays layout for SIMD-friendly access patterns
  * Optimized to reduce false sharing through thread-local state and separation of write paths
  * Improved L1 cache locality via contiguous memory and low-fragmentation allocation

* **Performance Profiling (optional)**:

  * `perf stat` integration: IPC, cache/TLB misses, branch mispredictions
  * Tracks cycles-per-trial and miss-per-trial metrics

* **Logging & Analysis**:

  * Zstandard-compressed Parquet output
  * Auto-generated CSV performance tables for quick inspection

* **CI Tested**: GitHub Actions verifies builds and logs per commit

* **Cross-platform**:

  * ✅ Linux, Windows (WSL), and macOS supported
  * ⚠️ Windows support (MSVC + Ninja) is experimental

---

### 🔧 Core Optimization Strategies

This section breaks down the internal optimizations that power the engine, with special focus on SIMD, memory, and cache-sensitive design.

---

## Core Optimizations

### 1. **Distance Check Formula**

Traditional distance check uses a square root:

```cpp
if (sqrt(x*x + y*y) <= 1.0)
```

This is replaced by:

```cpp
if (x*x + y*y) <= 1.0
```

**Why?**

* Removes expensive `sqrt()` call
* Enables vectorization (SIMD) and compiler auto-vectorization

---

### 2. **SIMD-Accelerated Trial Execution**

#### AVX2 (x86-64)

* Uses 256-bit registers (`__m256d`)
* 4 double-precision floats per SIMD batch
* Circle check is vectorized:

  ```cpp
  _mm256_add_pd(_mm256_mul_pd(x, x), _mm256_mul_pd(y, y)) <= 1.0
  ```
* Result: hit counts are derived via bitmask (`_mm256_movemask_pd`) and `__builtin_popcount`

#### NEON (ARM64)

* 128-bit registers (`float64x2_t`)
* 2 double-precision floats per batch
* Performs `vcleq_f64` and `vmulq_f64` in parallel

Both methods avoid conditional branches, pipeline stalls, and scalar overhead.

---

#### 3. **Bitmasking: Fast Hit Counting with No Branches**

After computing whether each dart is inside the circle, SIMD comparisons produce a **bitmask**:

```cpp
// For AVX2
__m256d cmp = _mm256_cmp_pd(...);
int mask = _mm256_movemask_pd(cmp);  // e.g., 0b1010 = 2 hits
int hits = __builtin_popcount(mask); // Fast hardware popcount
```

**Why bitmasking?**

* Replaces 4 conditional `if`s with a single integer mask
* Enables **branchless counting** in constant time
* Avoids CPU misprediction penalties from random dart throws
* Maps directly to native CPU instructions (fast + deterministic)

> Bitmasking is a classic SIMD pattern — perfect for Monte Carlo trials where each outcome is independent and binary.

---

### 4. **Memory Optimization: Pool Allocator**

#### What it does:

* Allocates from a fixed-size buffer using a **bump pointer**
* No `malloc`, `free`, or heap metadata
* Memory is reused every frame via `reset()`

#### Why it matters:

* Heap allocation causes:

  * Fragmentation
  * Lock contention in multithreaded workloads
  * Unpredictable latency due to OS-level bookkeeping

* PoolAllocator offers:

  * **O(1)** allocation
  * **Zero fragmentation**
  * **Cache-aligned** access (64-byte default)

⚠️ Note: For small types like int, the performance difference between heap and pool allocation is minimal, as the allocation cost is quickly amortized.

However, as object size increases—especially with larger structs, arrays, or cache-heavy data—the heap introduces significant overhead due to metadata, fragmentation, and poor locality.

In contrast, PoolAllocator maintains constant-time, contiguous allocation, making it dramatically faster and more cache-friendly for large or frequently reused types.

#### Performance Impact:

| Metric             | `new` / `malloc` | `PoolAllocator`              |
| ------------------ | ---------------- | ---------------------------- |
| Allocation Latency | Variable         | Constant (1 pointer bump)    |
| Cache Locality     | Unpredictable    | Strong (contiguous memory)   |
| SIMD Alignment     | Manual / fragile | Default (64B, AVX/NEON safe) |
| GC/Freeing         | Per-object       | Bulk reset (O(1))            |

---

### 5. **Thread-Local Everything (No Locks)**

Each simulation thread gets:

* Its own RNG (`std::mt19937_64`)
* Its own `PoolAllocator`
* No shared writes, no atomics

Benefits:

* **No false sharing**: Allocated data is 64B-aligned (cache line size)
* **No heap contention**: Each thread manages its own memory space
* **No synchronization**: All computation and memory state is isolated

> Threads join only at final result aggregation — no locks or mutexes are required at any step.

---

### 6. **Scalar Fallback for Remainders**

SIMD only works on batches (4 trials for AVX2, 2 for NEON).

To maintain precision:

* Remainder trials (`n % batch`) fall back to scalar logic
* Ensures all `n` trials are run without vector masking complexity

---

## Real-World Analogy: High-Frequency Trading (HFT)

This memory model mirrors arena allocators used in HFT systems:

* Allocate short-lived order/trade structs in a thread-local memory arena
* Reset per-tick or per-frame
* Avoid GC stalls or malloc overhead during latency-sensitive events

**Why it works here:**
Monte Carlo trials are **embarrassingly parallel** and short-lived — ideal for memory reuse and SIMD-style vectorization.

---

## Benchmark-Oriented Design Summary

| Feature               | Reason                                          |
| --------------------- | ----------------------------------------------- |
| `PoolAllocator`       | Minimal latency per alloc, avoids fragmentation |
| SIMD (AVX2/NEON)      | Process 2–4 trials per instruction cycle        |
| Thread-Local PRNG     | Avoids locking / shared access                  |
| No heap in hot path   | Eliminates OS allocator variability             |
| Aligned memory (64B)  | Safe for AVX/NEON, avoids false sharing         |
| `reset()` reuse model | Fast GC-like memory clearing in `O(1)`          |
| Scalar fallback       | Completes remaining trials without SIMD masking |

---

### 💡 Tip for Reviewers / Recruiters

The memory, parallelism, and vectorization strategies in this engine directly reflect patterns used in:

* **Market simulation platforms**
* **Order book matching engines**
* **ML Compilers (eg., Pytorch)**
* **HPC (High Performance Computing) workloads**

---

## Requirements

* CMake 3.15+
* Ninja
* Clang++ (recommended) or GCC 12+

---

## Setup Instructions
Note: `perf` is not supported on macOS or WSL. Use a bare metal Linux setup if you want benchmarking

### 🐧 Arch Linux

```bash
sudo pacman -S cmake ninja clang
```

---

### 🌀 Linux

```bash
sudo apt update
sudo apt install cmake ninja-build clang
```

### 🍎 macOS (with Homebrew)

```bash
brew install cmake ninja
```

---

### 🪟 Windows (WSL2 — ✅ Recommended)

**WSL (Windows Subsystem for Linux)** is fully supported. Setup is identical to Linux:

```bash
sudo apt update
sudo apt install cmake ninja-build clang python3-pip
```

> ✅ Clang and AVX2 work on WSL with native Linux tooling.
> ❌ Direct Windows builds are not supported due to lack of `std::aligned_alloc` and allocator trait compatibility.

### ⚠️ Windows (MSVC — Experimental)
Partial support via Ninja inside Developer Prompt:

```
cmake -G Ninja -B build
ninja -C build
```

Some allocators or SIMD intrinsics may require patching.

### ❌ Windows (MinGW)
MinGW is **not supported** due to lack of `std::aligned_alloc` and `std::allocator_traits` compatibility.

---

# Building & Running

### Build (Linux/macOS/WSL)
```
cmake -G Ninja -B build
ninja -C build
./build/montecarlo [TRIALS] [METHOD]

```

Running just `./build/montecarlo` runs all methods with `1,000,000,000` trials each by default. 

Note that `[TRIALS]` and `[METHOD]` are optional parameters and default to running `1,000,000,000` trials and all execution methods respectively. 

You can also singly test other execution models:

```
./build/montecarlo 100000000 Sequential
./build/montecarlo 100000000 Heap
./build/montecarlo 100000000 Pool
./build/montecarlo 100000000 SIMD
```

---

## 📊 Running Benchmark Suite (Optional)
This uses Linux perf and *requires bare metal Linux.*

Results are logged in .parquet (primarily for effiency) and partial support for .csv (for readability).

```
chmod +x scripts/run_perf.sh
./scripts/run_perf.sh              # runs all methods with 1,000,000,000 trials
./scripts/run_perf.sh [TRIALS] [METHODS]
./scripts/run_perf.sh 50000000 SIMD insert_db=false  # Skip ClickHouse inser
```

By default:

* All methods are benchmarked
* Results are exported as `.parquet` files
* Results are inserted into ClickHouse automatically each run. 

> Thus you must have Clickhouse already running with the specified configs from your .env file.
> You can do this by running `make init` or `make init_demo` if its your first time. Otherwise run `make up` (docker-compose up -d).

> Pass `insert_db=false` to skip inserting (e.g., for CI or dry runs).

Note that `/scripts/run_perf.sh [TRIALS] [METHODS]` is to be treated the same as running `./build/montecarlo [TRIALS] [METHODS]`

## 🐋 Docker (Optional for ClickHouse + Grafana Setup / Data Visualization)

> Used for dashboard visualization and log ingestion.

If you want to use the full monitoring pipeline:

1. Install Docker + Docker Compose
   👉 Follow instructions for your OS:

   * [Docker for Linux](https://docs.docker.com/engine/install/)
   * [Docker Desktop for macOS/Windows](https://www.docker.com/products/docker-desktop/)

**Benchmark Suite Snapshot**
![](https://files.catbox.moe/loir4s.png)

---

## 🛠️ Perf Dashboard Setup (Docker + Makefile)

This project includes a `Makefile` to manage your local Docker environment for setting up Clickhouse and loading data, log ingestion + visualization via ClickHouse and Grafana.

> 🧼 These commands manage everything from booting the stack to loading demo data and resetting volumes.

### 📋 Makefile Command Table

| Command                 | Description                                                           |
| ----------------------- | --------------------------------------------------------------------- |
| `make start`            | 🐳 Start Docker containers (ClickHouse, Grafana)                      |
| `make stop`             | 📦 Stop containers, **preserve data**                                 |
| `make rebuild`          | 🔄 Restart + rebuild images (data preserved)                          |
| `make reset_all`        | 🧼 Full reset (⚠️ **deletes volumes**) and rebuilds                   |
| `make clean_all`        | 🧹 Remove Docker volumes + local data (dangerous!)                    |
| `make clear_data`       | 📁 Deletes local simulation data only (`db/`)                         |
| `make clear_parquets`   | 🧽 Deletes all local `.parquet` logs                                  |
| `make logs`             | 📜 Streams Docker logs from all containers                            |
| `make init`             | 🌱 Start stack and initialize ClickHouse schema                       |
| `make init_demo`        | 🌸 Load sample data (`db_sample.parquet`) into ClickHouse             |
| `make load_data`        | 📥 Load your current simulation log (`db/db.parquet`) into ClickHouse |
| `make load_demo`        | 🧺 Load demo Parquet into `db/`, then into ClickHouse                 |
| `make setup_clickhouse` | 🛠️ Manually reinitialize ClickHouse schema                           |

> ⚠️ **Important:**
> Any of the following commands will **overwrite all current ClickHouse data** by reloading from `DB_PATH`:
> `make init_demo`, `make load_data`, `make load_demo`, or any command that invokes `scripts.setup --load-*`.

---

## 📄 Environment Configuration (`.env`)

You must configure your environment before running the Docker stack.

A `.env.sample` file is included. To get started:

```bash
cp .env.sample .env
```

> You may tweak the values, but they should work out of the box **if ports `9000`, `8123`, and `3000` are free**.

### Default `.env` Variables

```dotenv
# ClickHouse
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_UID=clickhouse-datasource

# For Python client
CLICKHOUSE_HOST=localhost
CLICKHOUSE_TCP_PORT=9000
CLICKHOUSE_HTTP_PORT=8123

# For Docker containers
CLICKHOUSE_HOST_DOCKER=clickhouse
CLICKHOUSE_TCP_PORT_DOCKER=9000
CLICKHOUSE_HTTP_PORT_DOCKER=8123

# Grafana
GRAFANA_PORT=3000

# Data paths
DB_PATH=db/db.parquet
SAMPLE_PATH=samples/db_sample.parquet
```

> If you experience port conflicts (e.g., port 3000 is in use), either:
>
> * Kill the conflicting service
> * Or **edit `.env`** to use alternate ports (and reflect those changes in your `docker-compose.yml`)

---

## 🤖 GitHub Actions CI

Every push or PR to `main` is automatically tested via GitHub Actions:

* Builds using Clang + CMake + Ninja on Ubuntu
* Runs a dry smoke test for all methods:

  ```bash
  ./build/montecarlo 10000 Sequential
  ./build/montecarlo 10000 Heap
  ./build/montecarlo 10000 Pool
  ./build/montecarlo 10000 SIMD
  ```
* CI ensures correctness, not benchmarking

CI badge and logs: [View GitHub Actions](https://github.com/yushasama/montecarlo-benchmarking-engine/actions)

---

## 📄 Performance Benchmark Snapshot

A sample snapshot is included for reference:
👉 [samples/perf_results_all_4ca37783.md](./samples/perf_results_all_4ca37783.md)

Note that markdowk files are not generated automatically, the markdown file was generated for
ease of display for this readme.

To inspect raw `.parquet` logs directly, explore files in:

```bash
samples/*.parquet
```

You can also view them visually via [https://www.tablab.app](https://www.tablab.app) — just drag and drop any `.parquet` file.

---