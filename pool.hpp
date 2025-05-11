// =======================================
// pool.hpp - Fast aligned memory pool
// =======================================
/**
 * @file pool.hpp
 * @brief Fast aligned bump allocator for high-performance simulations.
 *
 * Custom bump allocator used to replace `new` / `malloc` in hot paths.
 *
 * ## Features
 * - Fixed-size buffer with pointer bumping
 * - 64-byte alignment for cache lines + AVX
 * - No deallocation — just reset to reuse
 * - Ideal for short-lived, per-thread workloads
 *
 * ## Usage
 * ```cpp
 * PoolAllocator pool(64 * 1024);
 * MyStruct* ptr = pool.allocate<MyStruct>();
 * pool.reset();
 * ```
 *
 * ## Requirements
 * - C++17 or higher for `std::aligned_alloc`
*/

#pragma once

#include <cstddef>
#include <cstdlib>
#include <new>
#include <mutex>
#include <cassert>

/**
 * @brief Fast aligned bump allocator for multithreaded simulations.
 * 
 * Allocates memory from a preallocated buffer using pointer arithmetic.
 * All memory is aligned to 64 bytes to maximize cache and SIMD performance.
 */
struct PoolAllocator {
    char* memory;                     ///< Raw memory block
    std::size_t capacity;            ///< Total capacity in bytes
    std::size_t offset; ///< Offset for bump allocation

public:
    /**
     * @brief Construct a new PoolAllocator with a given size.
     * @param bytes Number of bytes to preallocate (must be multiple of 64)
     */
    explicit PoolAllocator(size_t bytes) {
        memory = static_cast<char*>(std::aligned_alloc(64, bytes));
        capacity = bytes;
        offset = 0;
        assert(memory && "Failed to allocate aligned memory");
    }
    
    /**
     * @brief Destroy the PoolAllocator and free the buffer.
     */
    ~PoolAllocator() {
        std::free(memory);
    }

    /**
     * @brief Allocates memory for type T with specified alignment (default = alignof(T)).
     * @tparam T Type of data.
     * @param align Alignment in bytes (default: alignof(T)).
     * @return Pointer to aligned memory or nullptr on overflow.
     */
    template<typename T>
    T* allocate(std::size_t align = alignof(T)) {
        std::size_t current = offset;
        offset += sizeof(T);  // 64-byte spacing to avoid false sharing
        
        if (current + sizeof(T) > capacity) return nullptr;

        char* ptr = memory + current;
        std::uintptr_t aligned = (reinterpret_cast<std::uintptr_t>(ptr) + (align - 1)) & ~(align - 1);
        
        return reinterpret_cast<T*>(aligned);
    }

    /**
     * @brief Reset the allocator to reuse buffer (memory).
     */
    void reset() {
        offset = 0;
    }
};