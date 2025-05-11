// ========================================
// main.cpp - Simulation Launcher
// ========================================
/**
 * @file main.cpp
 * @brief CLI runner for benchmarking Monte Carlo methods.
 *
 * Dispatches simulations by method (Sequential, Heap, Pool, SIMD).
 *
 * ## Usage
 * ```bash
 * ./montecarlo             # Run all methods (default trials)
 * ./montecarlo 5000000     # Run all methods with 5M trials
 * ./montecarlo 1e7 SIMD    # Run only SIMD
 * ```
 *
 * ## CLI Arguments
 * - `argv[1]` = number of trials (optional)
 * - `argv[2]` = method: Sequential, Heap, Pool, SIMD, or All (optional)
 *
 * ## Output
 * Each benchmark logs:
 * - π estimate
 * - Runtime in seconds + nanoseconds
*/

#include "montecarlo.hpp"
#include "benchmark.hpp"
#include <chrono>
#include <iostream>
#include <random>
#include <thread>
#include <unordered_set>
#include <vector>

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
                totalHits += *ptr;
            }

            return totalHits;
        });
    }

    return 0;
}
