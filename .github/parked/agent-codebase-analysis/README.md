# Agent codebase analysis (parked)

Not in use. GitHub only runs workflows directly under `.github/workflows/`, so
nothing in this folder runs.

`analyze_codebase.py` has a coding agent (claude/codex/opencode) statically audit a
source tree and write a RESOLVE `vulnerabilities.json`, plus one file per finding
under `cves/` for input synthesis. `analyze-codebase.yml` runs it inside the
`setup/Dockerfile` image.

To re-enable, move `analyze-codebase.yml` back into `.github/workflows/` and
`analyze_codebase.py` into `.github/scripts/`, then update the script path in the
"Analyze codebase" step. It needs an `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`)
repository secret.

The active pipeline uses the SBOM lookup instead: see
`.github/workflows/sbom-scan.yml`.
