cmake_minimum_required(VERSION 3.15)
project(MonteSim LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(APPLE)
    message(STATUS "Building on macOS, enabling libc++")
    add_compile_options(-stdlib=libc++ -O3 -Wall -Wextra)
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -stdlib=libc++")

elseif(UNIX)
    message(STATUS "Building on Linux / WSL / Unix-like system")
    add_compile_options(-O3 -Wall -Wextra)
    add_compile_definitions(USE_AVX)
    add_compile_options(-mavx2)

elseif(WIN32)
    message(STATUS "Building on Windows")
    add_compile_options(/O2 /W4)
    add_compile_definitions(USE_AVX)
    add_compile_options(-mavx2)
endif()

add_executable(montecarlo main.cpp)
