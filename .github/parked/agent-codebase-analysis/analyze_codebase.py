#!/usr/bin/env python3
# Copyright (c) 2026 Riverside Research.
# LGPL-3; See LICENSE.txt in the repo root for details.

"""Statically audit a source tree with a coding agent and emit a RESOLVE vulnerabilities.json.

Runs inside the RESOLVE runtime image (setup/Dockerfile) and produces the CVE
description files consumed by `resolve input-synthesis`. Standard library only,
so it runs under the image's bundled /opt/resolve/bin/python3 regardless of
which RESOLVE release is installed.

Output layout:
  <output>/vulnerabilities.json     all findings, RESOLVE vulnerabilities.json format
  <output>/report.md                reconciliation report with evidence per finding
  <output>/cves/<cve-id>.json       one single-entry document per finding, ready to
                                    pass as <cve_path> to `resolve input-synthesis`
  <output>/tmp/                     intermediate survey/candidate/critique reports
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Mirrors resolve-cli/src/resolve/crash_analyzer/utils.py
REQUIRED_VULNERABILITY_KEYS = {
    "cve-id",
    "cve-description",
    "package-name",
    "package-version",
    "cwe-id",
    "cwe-name",
    "affected-function",
    "affected-file",
    "remediation-strategy",
}

OPTIONAL_VULNERABILITY_KEYS = {
    "undesirable-function",
}

REMEDIATION_STRATEGIES = {
    "exit",
    "recover",
    "sat",
    "widen",
    "continue",
    "none",
    "wrap",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    prog = os.path.basename(sys.argv[0])

    parser = argparse.ArgumentParser(
        description="Audit a source tree with a coding agent and write a RESOLVE vulnerabilities.json "
        "for use by input synthesis.",
        epilog=f"""Examples:
  {prog} claude -s cJSON -o out/analysis
  {prog} codex -s cJSON -o out/analysis --max-findings 3 --focus "cJSON_Parse and print paths\"""",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "agent",
        choices=("claude", "codex", "opencode"),
        help="Coding agent backend to execute prompts with.",
    )
    parser.add_argument(
        "-s",
        "--source",
        dest="source_dir",
        type=Path,
        default=Path.cwd(),
        help="Path to the source tree to analyze (default: current directory).",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        type=Path,
        default=Path("out/analysis"),
        help="Destination directory for vulnerabilities.json, report.md and per-CVE files.",
    )
    parser.add_argument(
        "--max-findings",
        type=int,
        default=5,
        help="Upper bound on the number of vulnerabilities emitted (default: 5).",
    )
    parser.add_argument(
        "--focus",
        default="",
        help="Optional free-text hint narrowing the audit (components, functions, bug classes).",
    )
    parser.add_argument(
        "--model",
        default="",
        help="Optional model override passed through to the selected agent CLI.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output_path if it already exists.",
    )
    return parser.parse_args(argv)


# Mirrors resolve-cli/src/resolve/agent_utils/agent.py:run_agent
def run_prompt(agent: str, prompt: str, cwd: Path, model: str | None = None) -> None:
    print(prompt, flush=True)
    env = os.environ.copy()
    match agent:
        case "claude":
            agent_command = ["claude", "-p", "--dangerously-skip-permissions"]
        case "codex":
            agent_command = [
                "codex",
                "exec",
                "--config",
                'model_reasoning_effort="high"',
                "--yolo",
                "--skip-git-repo-check",
            ]
        case "opencode":
            env["OPENCODE_PERMISSION"] = json.dumps({"*": "allow"})
            agent_command = ["opencode", "run", "--agent", "build"]
        case _:
            raise ValueError(f"unknown agent {agent=}")
    if model:
        agent_command.extend(["--model", model])

    subprocess.run(agent_command + [prompt], cwd=cwd, env=env, check=True)


def require_file(path: Path, step: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"{step} did not produce required file: {path}")


def prepare_output_path(output_path: Path, overwrite: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        if not overwrite:
            raise RuntimeError(
                f"output_path already exists: {output_path}. Use --overwrite to replace it."
            )
        if output_path.is_dir():
            shutil.rmtree(output_path)
        else:
            output_path.unlink()


def validate_vulnerabilities_json(path: Path, max_findings: int) -> list[dict]:
    """Validate path against the RESOLVE schema and return its vulnerabilities."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc

    if not isinstance(document, dict) or set(document) != {"vulnerabilities"}:
        raise ValueError(f"{path} must be an object with exactly the top-level key 'vulnerabilities'")

    vulnerabilities = document["vulnerabilities"]
    if not isinstance(vulnerabilities, list):
        raise ValueError(f"{path} field 'vulnerabilities' must be an array")
    if len(vulnerabilities) > max_findings:
        raise ValueError(
            f"{path} has {len(vulnerabilities)} vulnerabilities; at most {max_findings} are allowed"
        )

    allowed_keys = REQUIRED_VULNERABILITY_KEYS | OPTIONAL_VULNERABILITY_KEYS
    seen_ids = set()
    for index, vuln in enumerate(vulnerabilities):
        if not isinstance(vuln, dict):
            raise ValueError(f"vulnerabilities[{index}] must be an object")

        missing = REQUIRED_VULNERABILITY_KEYS - set(vuln)
        extra = set(vuln) - allowed_keys
        if missing:
            raise ValueError(f"vulnerabilities[{index}] is missing required keys: {sorted(missing)}")
        if extra:
            raise ValueError(f"vulnerabilities[{index}] has unexpected keys: {sorted(extra)}")

        for key in vuln:
            if not isinstance(vuln[key], str) or not vuln[key]:
                raise ValueError(f"vulnerabilities[{index}].{key} must be a non-empty string")

        if not vuln["cwe-id"].isdecimal():
            raise ValueError(
                f"vulnerabilities[{index}].cwe-id must be a numeric string without a CWE- prefix"
            )
        if vuln["remediation-strategy"] not in REMEDIATION_STRATEGIES:
            raise ValueError(
                f"vulnerabilities[{index}].remediation-strategy must be one of "
                f"{sorted(REMEDIATION_STRATEGIES)}"
            )
        if vuln["cve-id"] in seen_ids:
            raise ValueError(f"vulnerabilities[{index}].cve-id {vuln['cve-id']!r} is duplicated")
        seen_ids.add(vuln["cve-id"])

    return vulnerabilities


def write_per_cve_files(vulnerabilities: list[dict], cves_dir: Path) -> list[Path]:
    """Split findings into single-entry documents, one per input-synthesis run."""
    cves_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for vuln in vulnerabilities:
        name = re.sub(r"[^A-Za-z0-9._-]", "_", vuln["cve-id"])
        path = cves_dir / f"{name}.json"
        path.write_text(json.dumps({"vulnerabilities": [vuln]}, indent=4) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def _common_context(source_dir: Path, output_path: Path, tmp_path: Path, focus: str) -> str:
    focus_line = f"\nAudit focus requested by the user: {focus}\n" if focus else ""
    return f"""
The source tree to audit is `{source_dir}` (your working directory).
{focus_line}
Output directory: `{output_path}`
Temporary analysis directory: `{tmp_path}`

General requirements:
- This is a static security audit whose findings will be handed to an input-synthesis pipeline that tries to build a concrete input triggering each one. Prefer memory-safety and arithmetic bugs reachable from external input (files, network, stdin, parsed strings, API arguments) over theoretical issues.
- Base every claim on source code you have actually read. Cite project-relative file paths and line numbers.
- You may build the project or write small throwaway harnesses under `{tmp_path}` to confirm suspicions, but do not modify, reformat, or commit anything inside `{source_dir}`, and do not create or update `AGENTS.md`, `CLAUDE.md`, or `OPENCODE.md` there.
- Do not invent package names, versions, functions, files, or root causes. Use `UNKNOWN` for package name or version only when the build files and source tree give no credible evidence.
- Exclude test code, examples, fuzz harnesses, and vendored third-party code unless the user's focus says otherwise.
"""


def run(
    agent: str,
    source_dir: Path,
    output_path: Path,
    max_findings: int,
    focus: str,
    overwrite: bool,
    model: str | None = None,
) -> list[Path]:
    if not source_dir.is_dir():
        raise ValueError(f"source directory does not exist: {source_dir}")
    if max_findings < 1:
        raise ValueError("--max-findings must be at least 1")

    source_dir = source_dir.resolve()
    output_path = output_path.resolve()
    prepare_output_path(output_path, overwrite)

    tmp_path = output_path / "tmp"
    tmp_path.mkdir(parents=True, exist_ok=True)
    print(f"Using temporary workspace: {tmp_path}")

    survey_path = tmp_path / "survey.md"
    candidates_path = tmp_path / "candidates.md"
    critique_path = tmp_path / "critique.md"
    vulnerabilities_path = output_path / "vulnerabilities.json"
    report_path = output_path / "report.md"
    common_context = _common_context(source_dir, output_path, tmp_path, focus)

    survey_prompt = f"""
{common_context}

# Your task

Survey the project and write `{survey_path}`. Include:
- Project/package name and version, with the build file or header that establishes them.
- Language(s), build system, and how to build and run the main targets.
- External input entry points (public API functions, `main`, file/network/stdin readers, parsers) and the call paths from them into the core logic.
- The functions most likely to contain memory-safety or arithmetic bugs: manual buffer management, length/offset arithmetic, recursion on untrusted data, integer conversions, string handling.

Do not report vulnerabilities in this stage.
"""
    run_prompt(agent, survey_prompt, source_dir, model=model)
    require_file(survey_path, "codebase survey")

    candidates_prompt = f"""
{common_context}

`{survey_path}` contains a survey of the project.

# Your task

Audit the high-risk code identified in the survey and write `{candidates_path}`: the strongest evidence-backed case for each candidate vulnerability, ranked most severe and most externally reachable first. Report no more than {max_findings * 2} candidates.

For each candidate include:
- Candidate ID using `CVE-<project>-00001`, incrementing for distinct root causes.
- Root-cause function and project-relative source file, with line numbers.
- The input condition that triggers it and the call path from an external entry point.
- CWE ID/name and why it is the most specific supported class.
- Suggested RESOLVE remediation strategy, and an `undesirable-function` if the dangerous operation is a callee such as `memcpy` or `strcpy`.

If you find no credible vulnerability, say so and explain what you checked.
"""
    run_prompt(agent, candidates_prompt, source_dir, model=model)
    require_file(candidates_path, "vulnerability candidates")

    critique_prompt = f"""
{common_context}

`{candidates_path}` contains candidate vulnerabilities.

# Your task

Write `{critique_path}`: a rigorous challenge of every candidate. Assume each one is a false positive and try to prove it by re-reading the code. Challenge:
- Bounds checks, length validation, or allocation sizing elsewhere on the path that prevent the bug.
- Call paths that cannot actually be reached from external input.
- Incorrect or overly broad CWE choices, wrong `affected-function`/`affected-file`, or wrong remediation strategy.
- Duplicates that share one root cause.

For every candidate, conclude CONFIRMED, REJECTED, or UNCERTAIN with the evidence for that verdict.
"""
    run_prompt(agent, critique_prompt, source_dir, model=model)
    require_file(critique_path, "candidate critique")

    final_prompt = f"""
{common_context}

Inputs:
- Survey: `{survey_path}`
- Candidates: `{candidates_path}`
- Critique: `{critique_path}`

# Your task

Reconcile the candidates with the critique, then write exactly two final artifacts:
1. `{vulnerabilities_path}`
2. `{report_path}`

Emit at most {max_findings} vulnerabilities: those that survived the critique, ranked most severe and most externally reachable first.

`{vulnerabilities_path}` must be valid JSON with this exact top-level shape:

{{
  "vulnerabilities": [
    {{
      "cve-id": "CVE-<project>-00001",
      "cve-description": "...",
      "package-name": "...",
      "package-version": "...",
      "cwe-id": "...",
      "cwe-name": "...",
      "affected-function": "...",
      "affected-file": "...",
      "remediation-strategy": "exit"
    }}
  ]
}}

JSON rules:
- Use hyphenated keys exactly as shown, not snake_case. Only `undesirable-function` may be added, and only when the unsafe operation is in a dangerous callee called by `affected-function`.
- Every value is a non-empty string. `cve-id` values are unique.
- `cwe-id` is the numeric string only, such as `121`, not `CWE-121`.
- `remediation-strategy` is one of: exit, recover, sat, widen, continue, none, wrap. Prefer `exit` unless the evidence supports another strategy; use `sat`/`widen` only for integer overflow.
- If no credible vulnerability survived, write exactly `{{"vulnerabilities":[]}}`.
- No comments, Markdown fences, confidence scores, trailing commas, or extra top-level keys.

Field rules:
- `cve-description` is what input synthesis reasons over, so make it specific: component and version, the external input and the exact condition on it that triggers the bug (sizes, lengths, byte values, nesting depth), the call path from the entry point, the root cause, the bug class, and the impact. Two to five sentences.
- `affected-function` is the root-cause function, not `main` or a libc/allocator frame.
- `affected-file` is the project-relative path of the file defining `affected-function`.

`{report_path}` is Markdown. It must list each emitted vulnerability with its JSON values and supporting evidence (file:line citations), explain why rejected candidates were dropped, and summarize remaining uncertainty.
"""
    run_prompt(agent, final_prompt, source_dir, model=model)
    require_file(vulnerabilities_path, "final vulnerabilities.json")
    require_file(report_path, "final analysis report")

    try:
        vulnerabilities = validate_vulnerabilities_json(vulnerabilities_path, max_findings)
    except ValueError as exc:
        print(f"vulnerabilities.json failed validation, asking the agent to repair it: {exc}")
        repair_prompt = f"""
`{vulnerabilities_path}` failed schema validation with this error:

{exc}

Fix `{vulnerabilities_path}` in place so it satisfies the rules below without changing the substance of the findings, and update `{report_path}` if you remove any finding.

{final_prompt}
"""
        run_prompt(agent, repair_prompt, source_dir, model=model)
        vulnerabilities = validate_vulnerabilities_json(vulnerabilities_path, max_findings)

    cve_paths = write_per_cve_files(vulnerabilities, output_path / "cves")
    print(f"Wrote {len(vulnerabilities)} vulnerabilities to {vulnerabilities_path}")
    for path in cve_paths:
        print(f"  {path}")
    return cve_paths


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run(
            agent=args.agent,
            source_dir=args.source_dir,
            output_path=args.output_path,
            max_findings=args.max_findings,
            focus=args.focus,
            overwrite=args.overwrite,
            model=args.model or None,
        )
    except subprocess.CalledProcessError as exc:
        print(f"agent failed with exit code {exc.returncode}")
        return exc.returncode if exc.returncode != 0 else 1
    except FileNotFoundError as exc:
        print(f"could not run agent CLI: {exc}")
        return 127
    except (RuntimeError, ValueError) as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
