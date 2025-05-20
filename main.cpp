// ========================================
// main.cpp - Simulation Launcher
// ========================================
/**
 * @file main.cpp
 * @brief CLI runner for benchmarking Monte Carlo simulation methods.
 *
 * Launches π-estimation simulations using various memory and threading strategies.
 * Allows selection of individual method or batch benchmarking across all methods.
 *
 * ## Usage
 * ```bash
 * ./montecarlo                     # Run all methods (default trials = 100M)
 * ./montecarlo 5000000            # Run all methods with 5M trials
 * ./montecarlo 1e7 SIMD           # Run only SIMD with 10M trials
 * ```
 *
 * ## CLI Arguments
 * - `argv[1]` — Number of simulation trials (optional, default: 100_000_000)
 * - `argv[2]` — Method name: `Sequential`, `Heap`, `Pool`, `SIMD`, or `All` (optional, default: All)
 *
 * ## Methods
 * - Sequential:     Single-threaded naive implementation
 * - Heap (Threaded): Threaded heap allocation per thread
 * - Pool (Threaded): Threaded use of a bump allocator (fast reuse, aligned)
 * - SIMD (Threaded): Threaded SIMD-enhanced Monte Carlo with vectorization
 *
 * ## Output
 * Each benchmark logs:
 * - Estimated π value
 * - Runtime in seconds and nanoseconds
 * - Total hits (inside circle) used to compute the estimate
 *
 * ## Notes
 * - Uses fixed thread count (4) for parallel methods
 * - AVX2/NEON support is detected at runtime and reported
 * - Each threaded method aggregates results manually
 */

#include "montecarlo.hpp"
#include "benchmark.hpp"
#include <chrono>
#include <iostream>
#include <random>
#include <thread>
#include <unordered_set>
#include <vector>

/**
 * @brief Prints detected platform architecture and SIMD capability.
 *
 * Detects and logs support for AVX2 (x86) or NEON (ARM) at runtime.
 * Helps validate compatibility for SIMD-accelerated paths.
 */
void print_arch_info() {
    std::cout << "[INFO] Detected platform: ";
    system("uname -m");

#if defined(__AVX2__)
    std::cout << "[INFO] SIMD: AVX2 enabled\n";
#elif defined(__ARM_NEON)
    std::cout << "[INFO] SIMD: NEON enabled\n";
#else
    std::cout << "[WARN] No SIMD support detected\n";
#endif
}

/**
 * @brief Entry point for running Monte Carlo simulations via CLI.
 *
 * Parses CLI arguments and dispatches benchmark runs using one of the
 * available simulation methods: Sequential, Heap, Pool, SIMD, or All.
 *
 * Runs timing and aggregation logic per method and prints π estimates
 * and execution times.
 *
 * @param argc Number of CLI arguments
 * @param argv Array of CLI argument strings
 * @return 0 on success, non-zero on invalid method or failure
 */
int main(int argc, char* argv[]) {
    print_arch_info();

    int totalTrials = 100'000'000;
    std::string method = "All";

    if (argc > 1) totalTrials = std::atoi(argv[1]);
    if (argc > 2) method = argv[2];

    std::unordered_set<std::string> validMethods = {
        "Sequential", "Heap", "Pool", "SIMD", "All"
    };
    if (!validMethods.count(method)) {
        std::cerr << "[ERROR] Unknown method: " << method << "\n";
        std::cerr << "Valid options: Sequential, Heap, Pool, SIMD, All\n";
        return EXIT_FAILURE;
    }

    int threadCount = 4;

    if (method == "Sequential" || method == "All") {
        benchmark("Sequential", totalTrials, [&]() {
            return monteCarloPI_SEQUENTIAl(totalTrials);
        });
    }

    if (method == "Heap" || method == "All") {
        benchmark("Heap (Threaded)", totalTrials, [&]() {
            std::vector<std::thread> threads;
            std::vector<int*> results(threadCount);
            int perThread = totalTrials / threadCount;

            for (int t = 0; t < threadCount; ++t) {
                threads.emplace_back([&, t]() {
                    results[t] = monteCarloPI_HEAP(perThread);
                });
            }

            for (auto& th : threads) th.join();

            int totalHits = 0;
            for (auto ptr : results) {
                totalHits += *ptr;
                delete ptr;
            }

            return totalHits;
        });
    }

    
    if (method == "Pool" || method == "All") {
        benchmark("Pool (Threaded)", totalTrials, [&]() {
            std::vector<std::thread> threads;
            std::vector<int*> results(threadCount);
            int perThread = totalTrials / threadCount;

            for (int t = 0; t < threadCount; ++t) {
                threads.emplace_back([&, t]() {
                    results[t] = monteCarloPI_POOL(perThread);
                });
            }

            for (auto& th : threads) th.join();

            int totalHits = 0;
            for (auto ptr : results) {
                // NOTE: No delete required — memory allocated from PoolAllocator
                totalHits += *ptr;
            }

            return totalHits;
        });
    }

    if (method == "SIMD" || method == "All") {
        benchmark("SIMD (Threaded)", totalTrials, [&]() {
            std::vector<std::thread> threads;
            std::vector<int*> results(threadCount);
            int perThread = totalTrials / threadCount;

            for (int t = 0; t < threadCount; ++t) {
                threads.emplace_back([&, t]() {
                    results[t] = monteCarloPI_SIMD(perThread);
                });
            }

            for (auto& th : threads) th.join();

            int totalHits = 0;
            for (auto ptr : results) {
                // NOTE: No delete required — memory allocated from PoolAllocator
                totalHits += *ptr;
            }

            return totalHits;
        });
    }

    return 0;
}
