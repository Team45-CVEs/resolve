# sbom-mixed

Python project with a C++ extension (`src/fastmath.cpp`, built with pybind11 through CMake).

| | |
|---|---|
| SBOM | `sbom.spdx.json` (SPDX 3, one package: pybind11 2.13.6) |
| Expected | Success, `cve-count` = `0` (no known pybind11 CVEs at the time of writing) |
| Tests | That a Python + C++ CMake build is handled like any other C++ project |

To make this a vulnerable case too, add a C/C++ dependency with a known CVE (for example cJSON 1.7.17) to both `CMakeLists.txt` and `sbom.spdx.json`.
