cmake_minimum_required(VERSION 3.14)
project(vulnapp C)

# Pin the vulnerable version so the result doesn't depend on the runner.
include(FetchContent)
FetchContent_Declare(cjson
  GIT_REPOSITORY https://github.com/DaveGamble/cJSON.git
  GIT_TAG        v1.7.17)
set(ENABLE_CJSON_TEST OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(cjson)

add_executable(vulnapp main.c)
target_link_libraries(vulnapp PRIVATE cjson)
target_include_directories(vulnapp PRIVATE ${cjson_SOURCE_DIR})

# TODO: generate sbom.spdx.json here with install(SBOM ...) once the team
# has CMake 4.3+ with CMAKE_EXPERIMENTAL_GENERATE_SBOM. Until then the
# committed sbom.spdx.json is hand-written in the same format.
