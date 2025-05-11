# Monte Carlo Benchmark Engine (AVX2 / NEON / Threaded)

[![CI](https://github.com/yushasama/montecarlo-benchmarking-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/yushasama/montecarlo-benchmarking-engine/actions)

A high-performance SIMD Monte Carlo simulation framework written in C++17, benchmarked via `perf` and Docker.

> 🔬 Originally extended from a Spring 2025 CSULB CECS 325 (Systems Programming) assignment by Neal Terrell.

## 🚀 Features

- SIMD support (AVX2, NEON)
- Memory model comparison (Heap vs. Pool)
- Multi-threaded execution
- `perf stat` integration (cycles, IPC, cache, TLB, branch metrics)
- Markdown log generation (`perf_results.md`)
- Containerized benchmarking via Docker + GHCR
- Cross-platform (macOS, Linux, Windows)

## 🛠 Usage

### 🔧 Build locally (Linux/macOS)

> Requires: `cmake`, `ninja`, and `clang++`

```bash
cmake -G Ninja -B build -DCMAKE_CXX_FLAGS="-O3 -march=native"
ninja -C build
./build/montecarlo 100000000 SIMD
```

### 🪟 Build on Windows (MSVC or MinGW)

> Requires: `CMake`, `Ninja`, and MSVC or MinGW

In **Developer Command Prompt** (MSVC):

```cmd
cmake -G "Ninja" -B build -DCMAKE_CXX_FLAGS="/O2"
ninja -C build
.uild\montecarlo.exe 100000000 SIMD
```

Or with **MinGW**:

```bash
cmake -G "MinGW Makefiles" -B build
mingw32-make -C build
.uild\montecarlo.exe 100000000 SIMD
```

### 🐳 Run in Docker

```bash
docker pull ghcr.io/yushasama/montecarlo-benchmarking-engine:latest
docker run --rm --privileged ghcr.io/yushasama/montecarlo-benchmarking-engine ./build/montecarlo 10000000 SIMD
```

### 📊 Run Full Benchmark Suite

```bash
chmod +x scripts/run_perf.sh
./scripts/run_perf.sh 100000000
```

---

## 🏁 Performance Snapshot

📄 [View full perf_results.md](./perf_results.md)

### Config
- Trials: 100000000
- Metrics: Full perf stat (L1, L2, branch, TLB, IPC, etc.)
- CPU: Docker Linux container
- Build: Clang++ -O3 -march=native

| Method | Cycles    | Instr      | IPC  | Wall Time (s) | Wall Time (ns) | L1 Miss % | L2 Miss % | Branch Miss % | TLB Miss % | Misses/Trial | Cycles/Trial |
|--------|-----------|------------|------|----------------|----------------|-----------|-----------|----------------|------------|----------------|--------------|
| SIMD   | 83708092  | 300000000  | 3.58 | 0.072774       | 72774000       | 0.91%     | 2.31%     | 0.84%          | 0.29%      | 0.25          | 8.37         |
