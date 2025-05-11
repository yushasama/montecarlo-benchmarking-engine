FROM ubuntu:22.04

# Install tooling
RUN apt update && apt install -y \
  clang \
  cmake \
  ninja-build \
  linux-tools-common \
  linux-tools-generic \
  build-essential \
  valgrind \
  curl

WORKDIR /app
COPY . .

# Configure + build using Ninja
RUN cmake -G Ninja -S . -B build -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_CXX_FLAGS="-O3"
RUN ninja -C build

# Run perf stat by default
CMD ["perf", "stat", "-e", "cache-references,cache-misses,instructions,cycles", "./build/montecarlo"]