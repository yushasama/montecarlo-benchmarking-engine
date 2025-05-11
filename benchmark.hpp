// ========================================
// benchmark.hpp - Timing Utility Wrapper
// ========================================
/**
 * @file benchmark.hpp
 * @brief Wall-clock + cycle-accurate benchmarking for performance profiling.
 *
 * Wraps a simulation function and logs:
 * - Wall time in nanoseconds + seconds
 * - CPU cycles (via rdtsc or cntvct_el0)
 * - π estimate from number of hits
 *
 * ## Features
 * - Cross-platform CPU cycle counting (x86 + ARM)
 * - High-resolution `std::chrono` timer
 * - Printable results for logging or scripting
 *
 * ## Example
 * ```cpp
 * benchmark("SIMD", 10000000, [&]() {
 *     return monteCarloPI_SEQUENTIAl(10000000);
 * });
 * ```
*/

#pragma once

#include <chrono>
#include <functional>
#include <iostream>
#include <string>

/**
 * @brief Benchmark wrapper that logs wall time and CPU cycles.
 *
 * Times the execution of a function using both std::chrono.
 * Outputs hit count and estimate of π.
 * duration in seconds and nanoseconds
 *
 * @param name      Name of the benchmark (e.g., "SIMD")
 * @param trials    Total number of Monte Carlo trials
 * @param func      Function that returns number of hits
 */
inline void benchmark(const std::string& name, int trials, std::function<int()> func) {
    auto start = std::chrono::high_resolution_clock::now();

    int hits = func();

    auto end = std::chrono::high_resolution_clock::now();

    double piEstimate = 4.0 * hits / trials;
    auto elapsed_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();

    std::cout << name << ":\n"
              << "  Trials: " << trials << "\n"
              << "  Hits: " << hits << "\n"
              << "  Estimate: " << piEstimate << "\n"
              << "  Time: " << (elapsed_ns / 1e9) << "s (" << elapsed_ns << " ns)\n";
}
