# sbom-python

Python-only project. It pins `requests==2.19.1` (CVE-2018-18074), but has no CMake build, so there is **no SBOM**.

| | |
|---|---|
| SBOM | None |
| Expected | Failure, with the error `SBOM not found: <path>` |
| Tests | That a project RESOLVE can't scan fails clearly instead of reporting 0 CVEs |

If the team later decides the action should accept SBOMs from Python tools (SPDX 2.3 from syft or GitHub's dependency graph), add one here and change the expected result.
