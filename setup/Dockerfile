# RESOLVE — user/runtime image
# ----------------------------------------------------------------------------
# Installs the prebuilt RESOLVE release plus everything needed to use it in a
# pipeline: resolvecc, resolve reach / remediate / get-facts / sbom / crash-
# analysis / input-synthesis, and the CMake+Ninja toolchain for the SBOM path.
#
# Pick the AI backend at build time with one arg (default: codex / OpenAI):
#   docker build -t resolve .                                 # codex (default)
#   docker build --build-arg AI_BACKEND=claude   -t resolve . # Claude Code
#   docker build --build-arg AI_BACKEND=opencode -t resolve . # opencode
#   docker build --build-arg AI_BACKEND=none     -t resolve . # no AI (hermetic)
#
# Run (mount your target source, e.g. a cJSON checkout, into /work):
#   docker run -it --rm -v "${PWD}:/work" -w /work resolve bash
#   (PowerShell: -v "${PWD}:/work" ; cmd.exe: -v "%cd%:/work")
#
# AUTH IS PROVIDED AT RUN TIME, never baked into the image:
#   OpenAI/codex : docker run -e OPENAI_API_KEY=sk-...   ...   
#   Claude       : docker run -e ANTHROPIC_API_KEY=sk-ant-... ...
# In CI, inject these from encrypted secrets, not plaintext.
# ----------------------------------------------------------------------------

FROM ubuntu:24.04

ARG RESOLVE_VERSION=v0.1.0
ARG AI_BACKEND=codex          # codex | claude | opencode | none
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/resolve/bin:${PATH}"

# --- Runtime dependencies --------------------------------------------------
#   bash coreutils clang llvm binutils zstd : the 5 RESOLVE runtime deps
#   ca-certificates curl git                : fetch release + let agents clone
#   cmake ninja-build pkg-config            : SBOM build path (CMake >= 4.3)
RUN apt-get update && apt-get install -y --no-install-recommends \
        bash coreutils clang llvm binutils zstd \
        ca-certificates curl git pkg-config cmake ninja-build \
    && rm -rf /var/lib/apt/lists/*

# resolvecc looks for `clang`/`clang++`; symlink if only clang-18 exists.
RUN command -v clang  >/dev/null || ln -sf "$(command -v clang-18)"  /usr/local/bin/clang;  \
    command -v clang++ >/dev/null || ln -sf "$(command -v clang++-18)" /usr/local/bin/clang++

# --- RESOLVE (pinned prebuilt release) -------------------------------------
RUN curl -fL \
      "https://github.com/riversideresearch/resolve/releases/download/${RESOLVE_VERSION}/resolve-linux-x86_64.tar.gz" \
      -o /tmp/resolve.tar.gz \
    && tar -C / -xzf /tmp/resolve.tar.gz \
    && rm /tmp/resolve.tar.gz \
    && resolve version

# --- AI backend (one of codex | claude | opencode | none) ------------------
# RESOLVE's agent stages shell out to the vendor CLI itself:
#   codex    -> `codex exec --yolo ...`                 (OpenAI Codex)
#   claude   -> `claude -p --dangerously-skip-permissions`  (Claude Code)
#   opencode -> `opencode run --agent build`            (opencode)
# codex/claude are npm packages, so Node is installed only when one is chosen.
RUN case "$AI_BACKEND" in \
      codex|claude) \
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
        apt-get install -y --no-install-recommends nodejs && \
        rm -rf /var/lib/apt/lists/* ;; \
    esac; \
    case "$AI_BACKEND" in \
      codex)    npm install -g @openai/codex          && codex  --version ;; \
      claude)   npm install -g @anthropic-ai/claude-code && claude --version ;; \
      opencode) curl -fsSL https://opencode.ai/install | bash ;; \
      none)     echo "No AI backend installed (hermetic image)." ;; \
      *) echo "ERROR: unknown AI_BACKEND='$AI_BACKEND' (use codex|claude|opencode|none)" >&2; exit 1 ;; \
    esac

WORKDIR /work
CMD ["bash"]
