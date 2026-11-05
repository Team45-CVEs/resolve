# sbom-c-vuln

C project that links **cJSON 1.7.17**, a version with a known CVE.

| | |
|---|---|
| SBOM | `sbom.spdx.json` (SPDX 3, one package: cJSON 1.7.17) |
| Expected | `cve-count` of 1 or more, including **CVE-2024-31755** (`cJSON_SetValuestring`) |
| Tests | The normal path: CVEs found, per-CVE files written |

`main.c` calls `cJSON_SetValuestring`, so later stages (reach) have a path to the vulnerable function.

Other cJSON CVEs may appear as NVD changes, so tests should check that CVE-2024-31755 is present, not that the count is exact.
