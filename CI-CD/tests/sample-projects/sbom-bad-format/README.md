# sbom-bad-format

A CycloneDX SBOM instead of SPDX. `resolve sbom` can't read it.

| | |
|---|---|
| SBOM | `sbom.cdx.json` (CycloneDX 1.5) |
| Expected | **Should fail.** Today it probably passes with `cve-count` = `0`, because `resolve sbom` prints "Could not ingest file" and still exits 0 |
| Tests | That an unreadable SBOM isn't reported as "no vulnerabilities" |

If this test passes with 0 CVEs, the SBOM script needs to check for that message (or for an empty package list) and fail.
