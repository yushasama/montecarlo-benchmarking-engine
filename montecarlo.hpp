// ========================================
// montecarlo.hpp - SIMD Monte Carlo Engine
// ========================================
/**
 * @file montecarlo.hpp
 * @brief SIMD Monte Carlo Engine — Benchmarking π estimation via multiple memory and compute models.
 *
 * Demonstrates Monte Carlo Pi estimation using various high-performance methods:
 * - Sequential execution
 * - Multithreading
 * - SIMD vectorization (AVX2 / NEON)
 * - Heap vs Pool memory allocation
 *
 * Originally extended from a Monte Carlo Pi simulation assignment
 * for CSULB CECS 325 (Systems Programming taught by Neal Terrell during Spring 2025), adapted by Leon.
 *
 * ## Features
 * - Supports both x86 (AVX2) and ARM (NEON) SIMD.
 * - Pluggable `PoolAllocator` for thread-local fast memory.
 * - Ideal for comparing memory models in simulation-heavy workloads.
 *
 * ## Implementations
 * - `monteCarloPI_SEQUENTIAl` — Scalar baseline.
 * - `monteCarloPI_HEAP` — Heap-based allocation.
 * - `monteCarloPI_POOL` — Bump-allocated thread-local memory.
 * - `monteCarloPI_SIMD` — Vectorized simulation using AVX2/NEON.
 *
 * ## Requirements
 * - `pool.hpp` — bump allocator used in pool-based variants.
 * - SIMD supported hardware.
 * - C++17 or higher for `std::aligned_alloc` used in pool.hpp.
 *
 * Compilation fails gracefully if SIMD is not supported.
*/

#pragma once

#include "pool.hpp"
#include <chrono>
#include <iostream>
#include <random>
#include <thread>
#include <memory>

#if defined(__AVX2__)
    #define USE_AVX
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
