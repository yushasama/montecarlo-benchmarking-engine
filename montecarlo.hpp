// ========================================
// montecarlo.hpp - SIMD Monte Carlo Engine
// ========================================
/**
 * @file montecarlo.hpp
 * @brief High-performance Monte Carlo π Estimation Engine — SIMD-accelerated, memory-optimized.
 *
 * This module implements several variants of Monte Carlo π estimation, each progressively optimized
 * for better instruction throughput, memory efficiency, and parallel execution.
 *
 * Originally derived from a CSULB CECS 325 assignment (Sequential + Heap), this version was
 * redesigned by Leon to incorporate modern systems-level techniques like SIMD vectorization,
 * thread-local memory pooling, and branchless logic.
 *
 * ---
 *
 * ## Implemented Methods
 * - `monteCarloPI_SEQUENTIAl(int)` — Scalar loop, stack-allocated
 * - `monteCarloPI_HEAP(int)`       — Threaded with `new` per-thread
 * - `monteCarloPI_POOL(int)`       — Threaded with thread-local bump allocator
 * - `monteCarloPI_SIMD(int)`       — Fully vectorized (AVX2 or NEON) using pooled memory
 *
 * ---
 *
 * ## Core Optimization Techniques
 *
 * ### 1. Branchless Circle Check
 * Instead of:
 * ```cpp
 * if (sqrt(x*x + y*y) <= 1.0) ...
 * ```
 * We use:
 * ```cpp
 * (x*x + y*y) <= 1.0
 * ```
 * - Avoids `sqrt()` (costly floating-point op)
 * - Reduces instruction count and branching
 * - Works seamlessly in SIMD registers
 *
 * ### 2. SIMD Vectorization (AVX2 & NEON)
 * Monte Carlo trials are processed in **batches**, not individually:
 *
 * #### AVX2 (x86)
 * - **256-bit registers** → 4 lanes of 64-bit doubles
 * - Compute `x² + y²` in parallel using `_mm256_*` intrinsics
 * - Compare lanes to `1.0`, extract 4-bit result mask with `_mm256_movemask_pd`
 * - Use `__builtin_popcount()` to count how many darts landed inside the circle
 *
 * #### NEON (ARM64)
 * - **128-bit registers** → 2 doubles per iteration
 * - Uses `vcleq_f64`, `vmulq_f64`, and `vgetq_lane_u64` for hit counting
 *
 * #### Why Bitmasks and Branchless Logic?
 * Traditional loops use `if` statements (branches). Modern CPUs use **branch predictors** to guess direction, but:
 * - Mispredictions cost 10s of cycles
 * - Unpredictable branches (like random dart throws) are poison for pipelines
 *
 * SIMD avoids branching:
 * - All conditionals are replaced with **vectorized compare + bitmask**
 * - Hit counts are reduced via bit tricks (not branching logic)
 * - This is **branchless execution** — deterministic, pipelined, fast
 *
 * ### 3. Scalar Fallback
 * SIMD can only process `N` trials per iteration (N = 4 for AVX2, 2 for NEON).
 * If `total_trials % N != 0`, we run the leftover trials using regular scalar code.
 * This ensures:
 * - Full simulation accuracy
 * - No need for conditional vector masking
 * - Simpler logic
 *
 * ---
 *
 * ## Memory Allocation Models
 *
 * ### Heap Allocation (`monteCarloPI_HEAP`)
 * - Allocates result with `new int` per thread
 * - Easy but slow: system allocator adds metadata + bookkeeping
 * - Poor memory reuse in tight, repeated simulations
 *
 * ### Pool Allocation (`monteCarloPI_POOL` / `SIMD`)
 * - Uses a **bump allocator** (`PoolAllocator`) — a fast linear memory model
 * - Allocates from a pre-allocated, 64-byte-aligned buffer
 * - Each `allocate<T>()` simply bumps a pointer
 * - No `delete`, no free lists, no fragmentation
 * - `reset()` clears everything in O(1)
 *
 * #### "Fast, Reusable, Avoids Fragmentation" Means:
 * - **Fast:** No malloc overhead — just pointer arithmetic
 * - **Reusable:** Same memory reused across iterations
 * - **No fragmentation:** Memory is packed linearly; no holes or gaps
 *
 * #### Performance Impact
 * - For `int` and other primitives, gains over heap are modest or nonexistent.
 * - But for larger structs, array batches, or systems with frequent reuse:
 *   - Pooling can significantly outperform heap
 *   - Cache locality improves (memory stays hot)
 *
 * #### HFT Example
 * In high-frequency trading (HFT) systems:
 * - Millions of order objects are allocated and discarded per second
 * - Fragmented heap allocation introduces latency and cache misses
 * - **Pool allocators** or **arena-style memory systems** are used to:
 *   - Reuse memory per frame
 *   - Avoid heap contention between threads
 *   - Ensure deterministic latency
 *
 * The same principle applies here: simulate 100M darts with tight memory control.
 *
 * ---
 *
 * ## Threading Strategy
 * - 4 threads are launched per simulation
 * - Each uses:
 *   - A thread-local RNG (`std::mt19937_64`)
 *   - Its own memory allocator (heap or pool)
 * - Final hit counts are summed after join
 * - This avoids synchronization and false sharing
 *
 * ---
 *
 * ## Thread Safety and Parallelism Model
 *
 * This engine is fully thread-safe by design. Each simulation method is dispatched across
 * multiple threads (typically 4), and **each thread is isolated in both compute and memory**:
 *
 * ### 1. Thread-Local PRNG
 * - Each thread uses its own instance of `std::mt19937_64`
 * - Declared as `thread_local`, so there's **no sharing or locking**
 * - Ensures deterministic randomness per-thread (no race conditions)
 *
 * ### 2. Thread-Local Memory Allocator
 * - `monteCarloPI_POOL` and `monteCarloPI_SIMD` use a `thread_local PoolAllocator`
 * - Allocators are independent: no shared state, no mutexes, no heap contention
 * - Memory is preallocated and reused via `reset()`, which is also thread-local
 *
 * ### 3. No Shared Writes
 * - Each thread returns its own hit count (via `int*`)
 * - Main thread aggregates totals **after** all threads join
 * - There are **no atomic variables, no critical sections, and no false sharing**
 *
 * ### 4. Minimal Cache Line Interference
 * - Because hit counts are per-thread, there's no contention on shared cache lines
 * - Memory is aligned (64 bytes in PoolAllocator) to avoid CPU cache thrashing
 *
 * ---
 *
 * ✅ Result:
 * - Safe parallelism without needing synchronization primitives
 * - High scalability on multi-core CPUs
 * - Deterministic, race-free simulation
 *
 * ## Memory Model Comparison
 * | Method    | Allocation Type   | Threaded | SIMD  | Notes                                                  |
 * |-----------|-------------------|----------|-------|---------------------------------------------------------|
 * | Sequential| Stack             | ❌       | ❌    | Scalar loop, no memory management                      |
 * | Heap      | new/delete        | ✅       | ❌    | Easy but slower, allocates per thread                  |
 * | Pool      | PoolAllocator     | ✅       | ❌    | Fast pointer bumping, reused memory, no malloc         |
 * | SIMD      | PoolAllocator     | ✅       | ✅    | Fully vectorized with aligned memory + memory pooling  |
 *
 * ---
 *
 * ## Requirements
 * - **C++17**: For `aligned_alloc`, `thread_local`, and uniform initialization
 * - **SIMD Backend:**
 *   - AVX2: Define `-DUSE_AVX` when compiling
 *   - NEON: Auto-enabled via `__ARM_NEON` macro on ARM CPUs
 * - Compilation will fail if no SIMD backend is present
 *
 * ---
 *
 * ## Academic Origin
 * The initial scalar and heap methods were part of a Monte Carlo π estimation assignment
 * for **CECS 325: Systems Programming (Spring 2025)** at CSULB, taught by Neal Terrell.
 *
 * This refactored version — including low latency optimizations such as memory allocation overhead, SIMD aware programming threading, and
 * systems-level benchmarking — was engineered by Leon to explore performance modeling,
 * real-time allocation patterns, and vectorized compute strategies.
 */


#pragma once

#include "pool.hpp"
#include <chrono>
#include <iostream>
#include <random>
#include <thread>
#include <memory>

#if defined(USE_AVX)
    #include <immintrin.h>
#elif defined(__ARM_NEON) || defined(__ARM_NEON__)
    #define USE_NEON
    #include <arm_neon.h>
#else
    #error "No SIMD instruction set supported. Compile with USE_AVX or USE_NEON"
#endif

/**
 * @brief Checks if a 2D point lies inside the unit circle.
 * 
 * @param x X-coordinate
 * @param y Y-coordinate
 * @return true if (x, y) lies inside the unit circle
 */
inline bool isInsideCircle(double x, double y) {
  return (x*x + y*y) <= 1.0;
}

#ifdef USE_AVX
/**
 * @brief AVX2-specific function that counts how many points in a 4-element SIMD batch lie inside the unit circle.
 * @param x Packed SIMD X-coordinates
 * @param y Packed SIMD Y-coordinates
 * @return Number of hits inside the circle [0–4]
 */
inline int countInsideCircle_AVX(__m256d x, __m256d y) {
    __m256d x2 = _mm256_mul_pd(x, x);
    __m256d y2 = _mm256_mul_pd(y, y);
    __m256d dist2 = _mm256_add_pd(x2, y2);
    __m256d ones = _mm256_set1_pd(1.0);
    __m256d cmp = _mm256_cmp_pd(dist2, ones, _CMP_LE_OQ);
    return __builtin_popcount(_mm256_movemask_pd(cmp));
}
#endif

#ifdef USE_NEON
/**
 * @brief NEON-specific function that counts how many points in a 2-element SIMD batch lie inside the unit circle.
 * @param x Packed SIMD X-coordinates
 * @param y Packed SIMD Y-coordinates
 * @return Number of hits inside the circle [0–2]
 */
inline int countInsideCircle_NEON(float64x2_t x, float64x2_t y) {
    float64x2_t x2 = vmulq_f64(x, x);
    float64x2_t y2 = vmulq_f64(y, y);
    float64x2_t dist2 = vaddq_f64(x2, y2);
    float64x2_t ones = vdupq_n_f64(1.0);
    uint64x2_t cmp = vcleq_f64(dist2, ones);
    return static_cast<int>(vgetq_lane_u64(cmp, 0) != 0) + static_cast<int>(vgetq_lane_u64(cmp, 1) != 0);
}
#endif

/**
 * @brief Estimates π using sequential dart throwing.
 * @param numberOfTrials Total number of darts to throw
 * @return Number of hits inside the circle
 */
int monteCarloPI_SEQUENTIAl(int numberOfTrials) {
    std::random_device rd {};
    std::default_random_engine engine {rd()};
    std::uniform_real_distribution<double> darts{0.0, 1.0};

    int hits = 0;
    for (int i = 0; i < numberOfTrials; ++i) {
        double dartX = darts(engine);
        double dartY = darts(engine);
        if (isInsideCircle(dartX, dartY)) ++hits;
    }
    return hits;
}

/**
 * @brief Estimates π using heap-allocated result storage.
 * @param numberOfTrials Total number of darts to throw
 * @return Pointer to heap-allocated int storing hits inside the circle
 */
inline int* monteCarloPI_HEAP(int numberOfTrials) {
    std::random_device rd {};
    std::default_random_engine engine {rd()};
    std::uniform_real_distribution<double> darts{0.0, 1.0};

    int hits = 0;
    for (int i = 0; i < numberOfTrials; ++i) {
        double dartX = darts(engine);
        double dartY = darts(engine);
        if (isInsideCircle(dartX, dartY)) ++hits;
    }
    return new int{hits};
}

/**
 * @brief Estimates π using a thread-local memory pool (bump allocator).
 * @param numberOfTrials Total number of darts to throw
 * @return Pointer to pool-allocated int storing hits inside the circle
 */
inline int* monteCarloPI_POOL(int numberOfTrials) {
    thread_local PoolAllocator pool(64 * 1024);
    pool.reset();

    int* hits = pool.allocate<int>();
    if (!hits) {
        std::cerr << "[ERROR] PoolAllocator ran out of memory!\n";
        std::exit(EXIT_FAILURE);
    }
    *hits = 0;

    std::random_device rd;
    std::default_random_engine engine{rd()};
    std::uniform_real_distribution<double> darts{0.0, 1.0};

    for (int i = 0; i < numberOfTrials; ++i) {
        double dartX = darts(engine);
        double dartY = darts(engine);
        if (isInsideCircle(dartX, dartY)) ++(*hits);
    }
    return hits;
}

/**
 * @brief Estimates π using SIMD acceleration (AVX2 or NEON) and pool-allocated result storage.
 * @param numberOfTrials Total number of darts to throw
 * @return Pointer to pool-allocated int storing hits inside the circle
 */
inline int* monteCarloPI_SIMD(int numberOfTrials) {
    thread_local PoolAllocator pool(64 * 1024);
    pool.reset();

    int* hits = pool.allocate<int>();
    if (!hits) {
        std::cerr << "[ERROR] PoolAllocator ran out of memory!\n";
        std::exit(EXIT_FAILURE);
    }
    *hits = 0;

    thread_local std::mt19937_64 engine(std::random_device{}());
    std::uniform_real_distribution<double> dist(0.0, 1.0);

    int batch;
    int loopEnd;

    #ifdef USE_AVX
    batch = 4;
    alignas(32) double randX[batch], randY[batch];
    loopEnd = numberOfTrials - (numberOfTrials % batch);

    for (int i = 0; i < loopEnd; i+= batch) {
        for (int j = 0; j < batch; ++j) {
            randX[j] = dist(engine);
            randY[j] = dist(engine);
        }
        __m256d dartX = _mm256_load_pd(randX);
        __m256d dartY = _mm256_load_pd(randY);
        *hits += countInsideCircle_AVX(dartX, dartY);
    }
    #elif defined(USE_NEON)
    batch = 2;
    alignas(16) double randX[batch], randY[batch];
    loopEnd = numberOfTrials - (numberOfTrials % batch);

    for (int i = 0; i < loopEnd; i += batch) {
        for (int j = 0; j < batch; ++j) {
            randX[j] = dist(engine);
            randY[j] = dist(engine);
        }
        float64x2_t dartX = vld1q_f64(randX);
        float64x2_t dartY = vld1q_f64(randY);
        *hits += countInsideCircle_NEON(dartX, dartY);
    }
    #endif 

    for (int i = loopEnd; i < numberOfTrials; ++i) {
        double dartX = dist(engine);
        double dartY = dist(engine);
        if (isInsideCircle(dartX, dartY)) ++(*hits);
    }
    return hits;
}
