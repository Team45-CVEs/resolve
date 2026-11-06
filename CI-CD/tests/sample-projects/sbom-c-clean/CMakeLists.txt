cmake_minimum_required(VERSION 3.14)
project(cleanapp C)

add_executable(cleanapp main.c)

# TODO: generate sbom.spdx.json here with install(SBOM ...) once the team
# has CMake 4.3+ with CMAKE_EXPERIMENTAL_GENERATE_SBOM.
