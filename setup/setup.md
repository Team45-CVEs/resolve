# RESOLVE — Quick Setup (Docker + Claude)

Build a container with RESOLVE, grab cJSON as a test target, log in to Claude, and
list the available RESOLVE commands. Works the same in a GitHub Codespace or on local Docker.

---

## 0. Prerequisites

- Docker available (built into Codespaces; locally, Docker Desktop).
- The `Dockerfile` from this repo.
- A Claude Pro/Max account (for subscription login) or an Anthropic API key.

---

## 1. Build the image (Claude backend)

From the repo root (where the `Dockerfile` lives):

```bash
docker build --build-arg AI_BACKEND=claude -t resolve:claude .
```

> The Dockerfile defaults to `codex`, so pass `--build-arg AI_BACKEND=claude` for the Claude CLI.
> Valid backends: `codex` | `claude` | `opencode` | `none`.

---

## 2. Grab cJSON (test target)

Clone it into your current folder so the container can see it:

```bash
git clone https://github.com/DaveGamble/cJSON
```

You should now have a `cJSON/` folder next to the Dockerfile.

---

## 3. Run the container

`-v "${PWD}:/work"` mounts your current folder into the container at `/work` (edits sync both ways).
The `claude-auth` volume persists your Claude login across runs.

```bash
docker run -it -v claude-auth:/root/.claude -v "${PWD}:/work" -w /work resolve:claude bash
```

- **PowerShell:** `-v "${PWD}:/work"` (same).
- **cmd.exe:** `-v "%cd%:/work"`.

You'll land at a `root@...:/work#` prompt. `ls` should show `cJSON/`.

> Using a subscription? Do **not** pass `-e ANTHROPIC_API_KEY=...` — an API key overrides the subscription login.

---

## 4. Log in to Claude (one time per auth volume)

Inside the container:

```bash
claude
```

1. Choose **"Claude account with subscription"** (or use an API key — see note below).
2. Open the printed **URL** in your own laptop browser (Ctrl/Cmd-click or copy-paste the full URL).
3. Approve, copy the **code** it shows, paste it back at the terminal prompt, Enter.
4. Type `/exit` to leave the Claude session.

> API key instead: skip this step and run the container with `-e ANTHROPIC_API_KEY=sk-ant-...`.

---

## 5. List the RESOLVE commands

```bash
resolve help
```

Use `resolve help <subcommand>` to see any one command's options.
