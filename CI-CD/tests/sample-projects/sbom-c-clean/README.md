# sbom-c-clean

C project with no third-party dependencies.

| | |
|---|---|
| SBOM | `sbom.spdx.json` (SPDX 3, no packages) |
| Expected | Success, `cve-count` = `0`, `cve-files` = `[]` |
| Tests | The zero-CVE path that lets later stages skip |

The result can't drift with NVD, because no packages are looked up.
