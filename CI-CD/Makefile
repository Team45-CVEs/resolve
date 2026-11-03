# Test commands for the RESOLVE CI/CD platform.
#
# Run from CI-CD/ (make test) or from the repo root (make -C CI-CD test).
# Every path below is worked out from this file's location, so both work.
#
#   make setup   create .venv and install the pinned test dependencies (once)
#   make unit    run the tests on this machine, no Docker (seconds)
#   make test    build the image from the repo-root Dockerfile and run the
#                tests inside it, the same steps as the CI image job
#   make clean   remove test results and caches
#
# Pass extra pytest options with PYTEST_ARGS, e.g. make unit PYTEST_ARGS="-k gitlab".
# Paths containing spaces are not supported by make.

# ----------------------------------------------------------------- paths ---

CI_CD_DIR   := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
REPO_ROOT   := $(abspath $(CI_CD_DIR)/..)
TESTS_DIR   := $(CI_CD_DIR)/tests
RESULTS_DIR := $(CI_CD_DIR)/test-results

# ------------------------------------------------------- settings you can override ---

# Python used only to create the virtual environment.
PYTHON      ?= python3
DOCKER      ?= docker
DOCKERFILE  ?= $(REPO_ROOT)/Dockerfile
# Dockerfile build stage to test.
TARGET      ?= runtime
# Local tag; CI tags the image with the commit SHA instead.
IMAGE       ?= toolbox:local
# Set to --break-system-packages if the image's Python was installed with apt (see README).
PIP_FLAGS   ?=
PYTEST_ARGS ?=

VENV := $(CI_CD_DIR)/.venv
ifeq ($(OS),Windows_NT)
  VENV_PYTHON := $(VENV)/Scripts/python.exe
else
  VENV_PYTHON := $(VENV)/bin/python
endif

# What runs inside the throwaway test container. It first checks the image has the
# scripts where tests/pytest.ini expects them (pythonpath = ../scripts, i.e.
# /action/scripts); without this check a missing folder shows up as the misleading
# "module 'ci_env' has no attribute '_VARIABLES'".
CONTAINER_TEST_CMD = \
  if [ ! -f /action/scripts/ci_env.py ]; then \
    echo 'error: /action/scripts/ci_env.py is not in the image. The Dockerfile must copy CI-CD/scripts/ to /action/scripts/.' >&2; \
    exit 2; \
  fi \
  && python3 -m pip install --no-cache-dir --quiet $(PIP_FLAGS) -r /action/tests/requirements.txt \
  && python3 -m pytest /action/tests -p no:cacheprovider --junitxml=/results/junit.xml $(PYTEST_ARGS)

# ---------------------------------------------------------------- targets ---

.PHONY: help setup unit image test tests clean

help:
	@echo "make setup   create .venv and install the test dependencies (run once)"
	@echo "make unit    run the tests on this machine, no Docker"
	@echo "make test    build the image and run the tests inside it, as CI does"
	@echo "make clean   remove test results and caches"
	@echo ""
	@echo "Extra pytest options: make unit PYTEST_ARGS=\"-k gitlab\""

setup:
	$(PYTHON) -m venv "$(VENV)"
	"$(VENV_PYTHON)" -m pip install --quiet -r "$(TESTS_DIR)/requirements.txt"
	@echo "Ready. Run 'make unit', or activate .venv and run pytest from tests/."

unit:
	@test -e "$(VENV_PYTHON)" || { echo "No virtual environment yet. Run 'make setup' first." >&2; exit 1; }
	cd "$(TESTS_DIR)" && "$(VENV_PYTHON)" -m pytest $(PYTEST_ARGS)

image:
	$(DOCKER) build -f "$(DOCKERFILE)" --target $(TARGET) -t $(IMAGE) "$(REPO_ROOT)"

test: image
	mkdir -p "$(RESULTS_DIR)"
	$(DOCKER) run --rm --entrypoint sh \
	  -v "$(TESTS_DIR):/action/tests:ro" \
	  -v "$(RESULTS_DIR):/results" \
	  $(IMAGE) \
	  -c "$(CONTAINER_TEST_CMD)"
	@echo "JUnit report: $(RESULTS_DIR)/junit.xml"

tests: test   # alias

clean:
	rm -rf "$(RESULTS_DIR)"
	find "$(CI_CD_DIR)" -path "$(VENV)" -prune -o -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf "$(TESTS_DIR)/.pytest_cache"
	