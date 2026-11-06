cmake_minimum_required(VERSION 3.15)
project(mixedapp CXX)

include(FetchContent)
FetchContent_Declare(pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG        v2.13.6)
FetchContent_MakeAvailable(pybind11)

pybind11_add_module(fastmath src/fastmath.cpp)

# TODO: generate sbom.spdx.json here with install(SBOM ...) once the team
# has CMake 4.3+ with CMAKE_EXPERIMENTAL_GENERATE_SBOM.
