#!/usr/bin/env python3
# Copyright (c) 2026 Riverside Research.
# LGPL-3; See LICENSE.txt in the repo root for details.

"""Pipeline stage: SBOM lookup.

Runs the existing `resolve sbom` tool on an SPDX SBOM, checks its output, and
writes one vulnerabilities.json per CVE so the input-synthesis stage can take
them one at a time.

Standard library only, so it runs under the RESOLVE image's bundled
/opt/resolve/bin/python3 (see action.yml) or any local Python 3.10+.

Outputs (in OUTPUT_DIR):
  vulnerabilities.json     all findings from `resolve sbom`
  cves/<CVE-ID>.json       one document per CVE, input to input synthesis
If GITHUB_OUTPUT / GITHUB_STEP_SUMMARY are set, also writes step outputs
(vulnerabilities-path, cve-count, cve-files) and a results table.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# --- TEMPORARY CONFIG -------------------------------------------------------
# Placeholder values until the rest of the pipeline's scripts and action.yml
# files exist. Each one can be overridden by an environment variable of the
# same name, which is how action.yml passes its inputs in.

# SPDX SBOM to scan.
SBOM_PATH = os.environ.get("SBOM_PATH", "examples/sbom/example.spdx.json")
# Where vulnerabilities.json and cves/ are written.
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "sbom-out")
# LLM used to fill in affected-file/affected-function: none | claude | gemini | ollama | opencode.
# claude reads ANTHROPIC_API_KEY, gemini reads GEMINI_API_KEY.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "none")
# Minimum CVSS v3 base score; empty means no minimum.
MIN_SCORE = os.environ.get("MIN_SCORE", "")
# Which CVE statuses to drop.
FILTER_REJECTED = os.environ.get("FILTER_REJECTED", "true") == "true"
FILTER_DISPUTED = os.environ.get("FILTER_DISPUTED", "false") == "true"
FILTER_DEFERRED = os.environ.get("FILTER_DEFERRED", "false") == "true"
# -----------------------------------------------------------------------------

# Keys downstream stages (input synthesis, reach, remediate) rely on.
REQUIRED_KEYS = {
    "cve-id",
    "cve-description",
    "cwe-id",
    "affected-function",
    "affected-file",
}


def run_sbom_lookup(sbom_path: Path, vulnerabilities_path: Path) -> None:
    command = ["resolve", "sbom", str(sbom_path), "-o", str(vulnerabilities_path)]
    if LLM_PROVIDER != "none":
        command += ["-L", LLM_PROVIDER]
    if MIN_SCORE:
        command += ["--min-score", MIN_SCORE]
    if FILTER_REJECTED:
        command.append("--filter-rejected")
    if FILTER_DISPUTED:
        command.append("--filter-disputed")
    if FILTER_DEFERRED:
        command.append("--filter-deferred")

    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, check=True)


def load_vulnerabilities(vulnerabilities_path: Path) -> list[dict]:
    if not vulnerabilities_path.is_file():
        raise RuntimeError(f"resolve sbom did not produce {vulnerabilities_path}")

    vulnerabilities = json.loads(vulnerabilities_path.read_text(encoding="utf-8"))["vulnerabilities"]
    for index, vuln in enumerate(vulnerabilities):
        missing = REQUIRED_KEYS - set(vuln)
        if missing:
            raise RuntimeError(
                f"vulnerabilities[{index}] is missing {sorted(missing)}. If the keys use "
                "underscores (cve_id), the installed resolve predates the hyphenated-key fix "
                "in resolve-cli/src/resolve/sbom/schema/vuln_spec.py."
            )
    return vulnerabilities


def write_per_cve_files(vulnerabilities: list[dict], cves_dir: Path) -> list[Path]:
    """One document per CVE, holding every CWE entry `resolve sbom` reported for it."""
    by_cve: dict[str, list[dict]] = {}
    for vuln in vulnerabilities:
        by_cve.setdefault(vuln["cve-id"], []).append(vuln)

    cves_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for cve_id, entries in sorted(by_cve.items()):
        path = cves_dir / f"{cve_id}.json"
        path.write_text(json.dumps({"vulnerabilities": entries}, indent=2) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def write_github_outputs(output_dir: Path, vulnerabilities: list[dict], cve_paths: list[Path]) -> None:
    if github_output := os.environ.get("GITHUB_OUTPUT"):
        cve_files = [str(p.relative_to(output_dir)) for p in cve_paths]
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"vulnerabilities-path={output_dir / 'vulnerabilities.json'}\n")
            f.write(f"cve-count={len(cve_paths)}\n")
            f.write(f"cve-files={json.dumps(cve_files)}\n")

    if step_summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        lines = [
            f"## SBOM scan: `{SBOM_PATH}`",
            "",
            f"Found **{len(cve_paths)}** CVEs ({len(vulnerabilities)} CVE/CWE entries).",
            "",
            "| CVE ID | CWE | Package | Version | Function | File |",
            "|---|---|---|---|---|---|",
        ]
        for v in vulnerabilities:
            lines.append(
                f"| {v['cve-id']} | CWE-{v['cwe-id']} {v.get('cwe-name', '')} "
                f"| `{v.get('package-name', '')}` | {v.get('package-version', '')} "
                f"| `{v['affected-function']}` | `{v['affected-file']}` |"
            )
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def main() -> int:
    sbom_path = Path(SBOM_PATH)
    output_dir = Path(OUTPUT_DIR)
    vulnerabilities_path = output_dir / "vulnerabilities.json"

    try:
        if not sbom_path.is_file():
            raise RuntimeError(f"SBOM not found: {sbom_path}")
        output_dir.mkdir(parents=True, exist_ok=True)

        run_sbom_lookup(sbom_path, vulnerabilities_path)
        vulnerabilities = load_vulnerabilities(vulnerabilities_path)
        cve_paths = write_per_cve_files(vulnerabilities, output_dir / "cves")
        write_github_outputs(output_dir, vulnerabilities, cve_paths)
    except subprocess.CalledProcessError as exc:
        print(f"resolve sbom failed with exit code {exc.returncode}")
        return exc.returncode
    except RuntimeError as exc:
        print(f"error: {exc}")
        return 1

    print(f"Wrote {len(cve_paths)} CVE files to {output_dir / 'cves'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
