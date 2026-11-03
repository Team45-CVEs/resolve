# RESOLVE tests

This folder holds the Python tests for the RESOLVE CI/CD platform: the core modules (`ci_env.py`, `logger.py`) and the target scripts (`action*.py`). This README covers running the tests and writing new ones.

## Contents

1. [Quick start](#quick-start)
2. [How testing is organised](#how-testing-is-organised)
3. [Running the tests](#running-the-tests)
4. [Folder layout](#folder-layout)
5. [Shared fixtures in conftest.py](#shared-fixtures-in-conftestpy)
6. [Writing a new test](#writing-a-new-test)
7. [Rules](#rules)
8. [Troubleshooting](#troubleshooting)

## Quick start

From the repo root:

```sh
cd CI-CD
make setup      # once: creates .venv and installs pytest
make unit       # run the tests on this machine, no Docker
make test       # run them inside the image, the same way CI does
```

You need **Python 3.12 or newer** (see [Troubleshooting](#troubleshooting) for why), and Docker for `make test`.

## How testing is organised

Every change is checked in stages, cheapest first:

| Stage | What it checks | When |
| --- | --- | --- |
| Local runs | `make unit` while working, `make test` before pushing | Before every push |
| Static checks and contract tests | YAML, shell and Dockerfile linting; every `action.yml` matches its script | Every commit |
| Unit tests in the image | Script and module logic, with the real tools installed | Pull requests and pushes to main |
| Smoke test | The image started exactly as a runner starts it | Pull requests and pushes to main |
| Real-world pipelines | The full tool on real C/C++ projects | Before each release |

The tests in this folder are the unit tests. They run in an image built from the repo-root `Dockerfile`, because that's exactly what each action builds when it runs. CI repeats every check, so a local pass is a strong hint, not a gate.

## Running the tests

### With make

The `Makefile` is in `CI-CD/`. Run it from there (`make test`) or from the repo root (`make -C CI-CD test`).

| Command | What it does |
| --- | --- |
| `make setup` | Creates `CI-CD/.venv` and installs the pinned packages from `tests/requirements.txt`. Run it once, and again whenever `requirements.txt` changes. |
| `make unit` | Runs the tests on your machine with the `.venv` Python. Takes seconds, needs no Docker. |
| `make test` | Builds the image from the repo-root `Dockerfile` and runs the tests inside it, the same steps as CI. `make tests` does the same. |
| `make clean` | Removes `test-results/` and Python caches. Keeps `.venv`. |

Pass extra pytest options with `PYTEST_ARGS`:

```sh
make unit PYTEST_ARGS="-k gitlab"
make test PYTEST_ARGS="-x"
```

Other settings can be overridden the same way:

| Setting | Default | Change it when |
| --- | --- | --- |
| `PYTHON` | `python3` | Your Python 3.12 has another name, e.g. `PYTHON=python3.12` or `PYTHON=py` on Windows |
| `IMAGE` | `toolbox:local` | You want a different local tag |
| `TARGET` | `runtime` | You want to test another Dockerfile stage |
| `PIP_FLAGS` | empty | The image's Python was installed with `apt` (see [Troubleshooting](#troubleshooting)) |

### With pytest directly

After `make setup`, activate the virtual environment and **run pytest from inside `tests/`** (or any folder below it):

```sh
cd CI-CD
source .venv/bin/activate          # Windows: .venv\Scripts\activate
cd tests
pytest
```

`tests/pytest.ini` tells pytest where the scripts are, and pytest only finds that file when it's run from `tests/` or below:

```ini
[pytest]
minversion = 8.0          # fail clearly on an older pytest
testpaths = .
pythonpath = ../scripts   # lets tests import ci_env, logger and the action scripts
```

Running plain `pytest` from `CI-CD/` or the repo root fails with `module 'ci_env' has no attribute '_VARIABLES'`. If you must start elsewhere, give the path: `pytest CI-CD/tests`.

Useful commands, all from `tests/`:

| Command | What it does |
| --- | --- |
| `pytest` | Run every test |
| `pytest ci_env` | Run one folder |
| `pytest ci_env/test_ci_env.py::test_detects_github` | Run one test |
| `pytest -k gitlab` | Run tests whose name contains `gitlab` |
| `pytest -x` | Stop at the first failure |
| `pytest --lf` | Rerun only the tests that failed last time |
| `pytest -v` | List every test by name as it runs |

Local runs don't use the real tools (cppcheck and others) unless you have them installed, so they don't replace `make test`.

### What make test does

`make test` builds the image, then starts a throwaway container from it:

```sh
docker build -f Dockerfile --target runtime -t toolbox:local .      # from the repo root
docker run --rm --entrypoint sh \
  -v "$PWD/CI-CD/tests:/action/tests:ro" \
  -v "$PWD/CI-CD/test-results:/results" \
  toolbox:local \
  -c "python3 -m pip install --no-cache-dir -r /action/tests/requirements.txt \
      && python3 -m pytest /action/tests -p no:cacheprovider --junitxml=/results/junit.xml"
```

This mounts `tests/` read-only, installs pytest into the container only (the image is never changed), and writes a JUnit report to `CI-CD/test-results/junit.xml`. Some details matter:

- **The image must have the scripts at `/action/scripts`.** `pythonpath = ../scripts` is worked out from `/action/tests`, so the Dockerfile must copy `CI-CD/scripts/` to `/action/scripts/`. `make test` checks this first and stops with a clear error if they're missing.
- `python3 -m pip` and `python3 -m pytest` make sure both use the same Python. `python3` works in both official Python images and `apt`-based ones, where plain `python` may not exist.
- `-p no:cacheprovider` stops pytest trying to save its cache into the read-only `tests/` folder.

## Folder layout

```
<repo root>/
├── Dockerfile                      # builds the image every action uses
└── CI-CD/
    ├── Makefile                    # make setup / unit / test / clean
    ├── .gitignore                  # .venv, test results, caches
    ├── scripts/                    # ci_env.py, logger.py, action*.py
    └── tests/
        ├── README.md
        ├── pytest.ini              # where scripts are, minimum pytest version
        ├── conftest.py             # shared fixtures for every test
        ├── requirements.txt        # pytest and test helpers, pinned
        ├── report.schema.json      # required structure of a report
        ├── test_contracts.py       # (planned) action.yml vs scripts
        ├── fixtures/               # fake projects used as test input
        │   └── simple-build/
        │       ├── src/hello.c
        │       └── dist/hello.txt
        ├── ci_env/
        │   ├── test_ci_env.py
        │   └── expected/
        │       ├── github_output.txt
        │       └── ci_outputs.env
        ├── logger/                 # (planned)
        │   ├── test_logger.py
        │   └── expected/
        │       └── annotations.txt
        └── actionN/                # (planned) one per target script
            ├── conftest.py         # fixtures used only by this action
            ├── test_actionN.py
            └── expected/
```

Each core module and each target script gets its own folder with its tests and an `expected/` folder of golden files: the exact output the tests compare against. Fixture projects stay in the shared `fixtures/` folder, because several scripts and the smoke test use the same ones.

Note that `tests/fixtures/` holds **files** (fake projects), while pytest **fixtures** are setup functions. The names are similar but they're different things.

### Test data files

| File or folder | What it is |
| --- | --- |
| `fixtures/` | Small fake projects used as test input. `simple-build` is a one-file C project with a tiny `dist/` build. Tests copy one into a temporary workspace with `fixture_project`, so they can change it freely. |
| `<module>/expected/` | Golden files: the exact output one module or script should produce. When an output format changes on purpose, update its golden file in the same commit. |
| `report.schema.json` | A JSON Schema of the fields every report must have. Tests validate reports against it, so a missing or misnamed field fails even when values differ. It starts with `metadata` (exactly what `ci_env.metadata()` returns) and an optional `findings` count; add each report's own fields as the scripts are written. Validating needs the `jsonschema` package; add it to `requirements.txt`, pinned, with the first test that uses it. |
| `requirements.txt` | pytest and other test helpers, pinned to exact versions so results don't change when a new release comes out. |

`CI-CD/.gitignore` keeps the fixtures' `dist/` folders in git even if the repo ignores `dist/` elsewhere.

## Shared fixtures in conftest.py

`conftest.py` is loaded by pytest automatically. Any fixture in it can be used by every test below `tests/`, with no import: name the fixture as a parameter of your test function and pytest runs it first and passes in the result. **Never import `conftest.py`.**

| Fixture | Gives you |
| --- | --- |
| `github_env` | A simulated GitHub Actions step |
| `gitlab_env` | A simulated GitLab CI job |
| `local_env` | A run outside CI, with every CI variable removed |
| `fixture_project` | A function that copies a project from `tests/fixtures/` into the workspace |

### github_env, gitlab_env and local_env

Each one clears every CI variable from the environment, sets the ones its platform needs, and reloads `ci_env` so its values match. When the test ends, every change is undone and `ci_env` is reloaded again, so nothing leaks into the next test, even if the test fails.

| | `github_env` | `gitlab_env` | `local_env` |
| --- | --- | --- | --- |
| Platform flag | `GITHUB_ACTIONS=true` | `GITLAB_CI=true` | none |
| Workspace | `GITHUB_WORKSPACE` → a temp folder | `CI_PROJECT_DIR` → a temp folder | none |
| Outputs go to | `GITHUB_OUTPUT` → an empty temp file | `ci_outputs.env` in the workspace (created on first write) | printed |

Each fixture returns an object with:

| Attribute or method | What it is |
| --- | --- |
| `.platform` | `"github"`, `"gitlab"` or `"local"` |
| `.workspace` | The workspace folder (a `Path`), or `None` for `local_env` |
| `.output_file` | The file `set_output()` writes to, or `None` for `local_env` |
| `.set(NAME=value, ...)` | Set variables and reload `ci_env` in one step. `None` removes a variable. |

Setting a variable and reading it back:

```python
import ci_env

def test_reads_commit_sha(github_env):
    github_env.set(GITHUB_SHA="abc123")
    assert ci_env.COMMIT_SHA == "abc123"
```

Inputs use `INPUT_<NAME>` on GitHub and the bare name on GitLab:

```python
def test_reads_build_path_input(github_env):
    github_env.set(INPUT_BUILD_PATH="dist")
    assert ci_env.get_input("build_path") == "dist"

def test_reads_build_path_input_on_gitlab(gitlab_env):
    gitlab_env.set(BUILD_PATH="dist")
    assert ci_env.get_input("build_path") == "dist"
```

Names that aren't valid Python keywords, such as inputs with hyphens, go in a dict:

```python
def test_hyphenated_input(github_env):
    github_env.set(**{"INPUT_BUILD-PATH": "dist"})
    assert ci_env.get_input("build-path") == "dist"
```

Checking what `set_output()` wrote:

```python
def test_writes_report_file_output(github_env):
    ci_env.set_output("report_file", "build-report.json")
    assert "report_file<<" in github_env.output_file.read_text(encoding="utf-8")

def test_writes_dotenv_output(gitlab_env):
    ci_env.set_output("findings", 3)
    assert gitlab_env.output_file.read_text(encoding="utf-8") == "findings=3\n"

def test_prints_outputs_locally(local_env, capsys):
    ci_env.set_output("findings", 3)
    assert capsys.readouterr().out == "[output] findings=3\n"
```

Removing a variable the fixture set, for example to test what happens without `GITHUB_OUTPUT`:

```python
def test_missing_output_file(github_env):
    github_env.set(GITHUB_OUTPUT=None)
    ...
```

### Read values through the module

`ci_env` reads the environment once, when it is imported, and the fixtures reload it to pick up new values. Reloading updates the module, but not copies taken from it. So always read values as `ci_env.COMMIT_SHA`:

```python
import ci_env                    # good: ci_env.COMMIT_SHA follows every reload
from ci_env import COMMIT_SHA    # bad: keeps the value from when the file loaded
```

This applies to **target scripts as well as tests**. A script that does `from ci_env import WORKSPACE` at the top captures the workspace once, before any fixture runs, and its tests will see the wrong folder. Scripts should `import ci_env` and use `ci_env.WORKSPACE`.

You don't need to call `importlib.reload(ci_env)` yourself; `.set()` does it.

### fixture_project

Returns a function that copies a project from `tests/fixtures/<name>` into `tmp_path/workspace`, which is the same folder `github_env` and `gitlab_env` use as the workspace. Use them together and the project lands where the script expects it. The test gets its own copy, so it can change files freely.

```python
def test_project_lands_in_workspace(github_env, fixture_project):
    project = fixture_project("simple-build")
    assert project == github_env.workspace
    assert (github_env.workspace / "dist").is_dir()
```

Asking for a project that doesn't exist raises a `ValueError` naming the fixtures folder.

### pytest's built-in fixtures

These come with pytest and are requested by name in the same way.

| Fixture | Use it for |
| --- | --- |
| `tmp_path` | A new, empty folder for this test only |
| `monkeypatch` | Temporary changes undone when the test ends: `setenv`, `delenv`, `setattr`, `chdir` |
| `capsys` | Capturing printed output, e.g. logger's annotation lines |

Inside a `github_env`/`gitlab_env`/`local_env` test, prefer `.set()` over `monkeypatch.setenv` for CI variables, because `.set()` also reloads `ci_env`. A plain `monkeypatch.setenv` has no effect on `ci_env` until it is reloaded.

## Writing a new test

### A new target script

Create a folder with the same shape as the others:

```
tests/actionN/
├── test_actionN.py
├── conftest.py          # only if this action needs its own fixtures
└── expected/
```

A typical test copies a fixture project, sets the inputs, runs the script, and compares the result with a golden file. The example below is illustrative; replace `build_report.main()` with however your script is called:

```python
import json
from pathlib import Path

import ci_env
import build_report

EXPECTED = Path(__file__).parent / "expected"
EXPECTED_REPORT = EXPECTED / "simple-build-report.json"

def test_report_for_simple_build(github_env, fixture_project):
    """The report for the simple-build project matches the golden file."""
    fixture_project("simple-build")
    github_env.set(INPUT_BUILD_PATH="dist")

    build_report.main()

    actual = json.loads((github_env.workspace / "build-report.json").read_text(encoding="utf-8"))
    assert actual == json.loads(EXPECTED_REPORT.read_text(encoding="utf-8"))
```

Keep the paths to golden files as constants at the top of the test file, as above. When the report format changes on purpose, update the golden file in the same commit.

### Fixtures for just one folder

Setup used by only one action goes in that folder's own `conftest.py`. It can use the shared fixtures too:

```python
# tests/actionN/conftest.py
import pytest

@pytest.fixture
def report_path(github_env):
    """Where this action writes its report."""
    return github_env.workspace / "build-report.json"
```

Setup used by more than one folder belongs in the top-level `conftest.py`.

### Code that runs external tools

Logic that works on a tool's output (parsing, counting findings, building the report) is tested with a fake `subprocess.run`, so the test is fast and doesn't depend on the tool's version:

```python
import subprocess

def test_parses_findings(monkeypatch):
    fake_xml = "<results><error id='nullPointer' severity='error'/></results>"

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr=fake_xml)

    monkeypatch.setattr(subprocess, "run", fake_run)
    ...
```

This only works if the script calls `subprocess.run(...)`. A script that does `from subprocess import run` keeps its own copy, and the fake never reaches it.

Tests that run the real tool on a fixture project need the tool installed, so run them with `make test`.

### Document every test

Give each test a docstring saying what it checks and why, as in `ci_env/test_ci_env.py`. pytest shows the test name in failures, and the docstring tells the next person what broke.

## Rules

- **No test may depend on a secret.** Pull requests from forks can't access secrets, so those tests would fail for outside contributors.
- **Shared setup goes in a `conftest.py` fixture**, not copied between test files.
- **Scripts must give the same output for the same input**, or golden-file comparisons can't work. Anything random, such as the delimiter `set_output()` uses on GitHub, has to be pinned in the test. `ci_env/test_ci_env.py` shows how with its `fixed_uuid` fixture.
- **Test dependencies are pinned** to exact versions in `requirements.txt`. To add one, add it there with its version, then run `make setup` again.
- **Read `ci_env` values through the module**, in tests and scripts alike.

## Troubleshooting

**`AttributeError: module 'ci_env' has no attribute '_VARIABLES'`**
pytest couldn't find `ci_env.py`. Because `tests/ci_env/` is a folder with the same name, Python imports that folder as an empty package instead, and the error doesn't mention the real cause. Check that you're running pytest from `tests/`, or use `make unit`.

**`error: /action/scripts/ci_env.py is not in the image`**
From `make test`: the Dockerfile doesn't copy the scripts to where the tests expect them. It needs `COPY CI-CD/scripts/ /action/scripts/` (or an equivalent).

**`SyntaxError` when importing `ci_env`**
Your Python is older than 3.12. The `get_input()` line in `ci_env.py` reuses double quotes inside an f-string, which only 3.12 and newer accept. Use Python 3.12+, or change the inner quotes to single quotes and any Python 3 will work.

**`error: externally-managed-environment` from pip**
The Python was installed by the operating system (`apt`), which blocks system-wide installs. Locally, use `make setup`, which installs into `.venv` instead. In `make test`, run `make test PIP_FLAGS=--break-system-packages`; that's safe there because it only changes the throwaway container.

**`No virtual environment yet. Run 'make setup' first.`**
`make unit` needs the `.venv` that `make setup` creates.

**`PytestCacheWarning: could not create cache path`**
pytest is trying to save its cache into the read-only `tests/` mount. `make test` already passes `-p no:cacheprovider`; add it if you run the container by hand.

**A test marked `xfail` in the results**
`test_gitlab_input_does_not_collide_with_system_variables` documents a known bug: on GitLab and locally, `get_input("path")` returns the system `PATH`. It's expected to fail. Once `get_input()` is fixed it will start passing, and because it's marked `strict=True` the suite will then fail as a reminder to remove the marker.

**A test passes alone but fails in the full run, or the other way round**
Something is leaking between tests. Make sure the test uses `github_env`, `gitlab_env` or `local_env` rather than setting CI variables with `monkeypatch` directly, and that it reads values as `ci_env.X` rather than importing them.