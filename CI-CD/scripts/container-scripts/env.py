import os 
import uuid 
from pathlib import Path 


# ------------------------------------------------------------ the mapping --- 
# Neutral name -> the environment variable each platform uses for it. 

_VARIABLES = { 
    #  neutral name    GitHub Actions                     GitLab CI 
    "WORKSPACE":   {"github": "GITHUB_WORKSPACE",  "gitlab": "CI_PROJECT_DIR"}, 
    "COMMIT_SHA":  {"github": "GITHUB_SHA",        "gitlab": "CI_COMMIT_SHA"}, 
    "REF_NAME":    {"github": "GITHUB_REF_NAME",   "gitlab": "CI_COMMIT_REF_NAME"}, 
    "REPOSITORY":  {"github": "GITHUB_REPOSITORY", "gitlab": "CI_PROJECT_PATH"}, 
    "RUN_ID":      {"github": "GITHUB_RUN_ID",     "gitlab": "CI_PIPELINE_ID"}, 
    "RUN_NUMBER":  {"github": "GITHUB_RUN_NUMBER", "gitlab": "CI_PIPELINE_IID"}, 
    "JOB_NAME":    {"github": "GITHUB_JOB",        "gitlab": "CI_JOB_NAME"}, 
    "EVENT":       {"github": "GITHUB_EVENT_NAME", "gitlab": "CI_PIPELINE_SOURCE"}, 
    "ACTOR":       {"github": "GITHUB_ACTOR",      "gitlab": "GITLAB_USER_LOGIN"}, 
    "SERVER_URL":  {"github": "GITHUB_SERVER_URL", "gitlab": "CI_SERVER_URL"}, 
} 


def _detect_platform(): 
    if os.environ.get("GITHUB_ACTIONS") == "true": 
        return "github" 
    if os.environ.get("GITLAB_CI") == "true": 
        return "gitlab" 
    return "local" 


def _read(neutral_name): 
    """Value of the platform's variable for this neutral name, or None.""" 
    variable = _VARIABLES[neutral_name].get(PLATFORM) 
    if variable is None: 
        return None 
    return os.environ.get(variable) or None   # treat an empty value as missing 

 

# ------------------------------------------------- values saved at import --- 

PLATFORM = _detect_platform()      # "github", "gitlab" or "local" 


_workspace = _read("WORKSPACE") 
WORKSPACE = Path(_workspace).resolve() if _workspace else None   # the shared mount 


COMMIT_SHA = _read("COMMIT_SHA") 
REF_NAME = _read("REF_NAME")        # branch or tag being built 
REPOSITORY = _read("REPOSITORY")    # "owner/repo" on GitHub, "group/project" on GitLab 
RUN_ID = _read("RUN_ID") 
RUN_NUMBER = _read("RUN_NUMBER")    # sequential run count within the project 
JOB_NAME = _read("JOB_NAME") 
EVENT = _read("EVENT")              # what triggered the run, e.g. "push" 
ACTOR = _read("ACTOR")              # user who triggered the run 
SERVER_URL = _read("SERVER_URL") 


IS_DEBUG = os.environ.get("RUNNER_DEBUG") == "1" or os.environ.get("CI_DEBUG_TRACE") == "true" 


def metadata(): 
    """All saved values as a dict, handy for reports.""" 
    return { 
        "platform": PLATFORM, 
        "workspace": str(WORKSPACE) if WORKSPACE else None, 
        "commit_sha": COMMIT_SHA, 
        "ref_name": REF_NAME, 
        "repository": REPOSITORY, 
        "run_id": RUN_ID, 
        "run_number": RUN_NUMBER, 
        "job_name": JOB_NAME, 
        "event": EVENT, 
        "actor": ACTOR, 
        "server_url": SERVER_URL, 
    } 

 
# --------------------------------------------------------------- inputs --- 
 

def get_input(name, default=None): 
    """Read an input. Same convention on every platform: INPUT_<NAME>. 
    GitHub sets these from the action's inputs; on GitLab, set them in the 
    job's variables, e.g. BUILD_PATH: dist.""" 
    value = os.environ.get(f"{'INPUT_' if PLATFORM == 'github' else ''}{name.upper()}", "").strip() 
    return value or default 

 
# -------------------------------------------------------------- outputs --- 


_GITLAB_OUTPUT_FILE = os.environ.get("CI_ENV_OUTPUT_FILE", "ci_outputs.env")    # Will need to have this set as a variable in gitlabs 
 

def set_output(name, value): 
    """Pass a value to later steps or jobs.""" 
    value = str(value) 

    if PLATFORM == "github": 
        delimiter = f"EOF_{uuid.uuid4().hex}"   # heredoc form allows multi-line values 
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f: 
            f.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n") 

    elif PLATFORM == "gitlab": 
        if "\n" in value: 
            raise ValueError(f"GitLab dotenv outputs must be one line: '{name}'") 
        with open((WORKSPACE or Path.cwd()) / _GITLAB_OUTPUT_FILE, "a", encoding="utf-8") as f: 
            f.write(f"{name}={value}\n") 

    else: 
        print(f"[output] {name}={value}") 

 

 