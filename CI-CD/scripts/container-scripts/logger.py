from contextlib import contextmanager 

# ---------------------------------------------------------------- helpers --- 
# GitHub reads specially formatted lines ("workflow commands") from the output. 
# These characters would break a command, so they must be escaped. 

def _escape_message(text): 
    return str(text).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A") 


def _escape_property(value): 
    return _escape_message(value).replace(":", "%3A").replace(",", "%2C") 


def _command(name, message, **properties): 
    """Print a workflow command, e.g. ::warning file=a.py,line=3::Some text""" 
    github_names = {"end_line": "endLine", "end_col": "endColumn"} 
    pairs = [ 
        f"{github_names.get(key, key)}={_escape_property(value)}" 
        for key, value in properties.items() 
        if value is not None 
    ] 
    props = (" " + ",".join(pairs)) if pairs else "" 
    print(f"::{name}{props}::{_escape_message(message)}", flush=True) 


# ------------------------------------------------------------- log levels --- 

def debug(message): 
    """Detailed output. Hidden unless step debug logging is enabled 
    (set the ACTIONS_STEP_DEBUG secret or variable to true).""" 
    _command("debug", message) 

 
def info(message): 
    """Normal log output.""" 
    print(message, flush=True) 

 
def notice(message, file=None, line=None, col=None, end_line=None, end_col=None, title=None): 
    """Something worth highlighting that is not a problem.""" 
    _command("notice", message, file=file, line=line, col=col, 
             end_line=end_line, end_col=end_col, title=title) 

 
def warning(message, file=None, line=None, col=None, end_line=None, end_col=None, title=None): 
    """A problem that does not fail the step.""" 
    _command("warning", message, file=file, line=line, col=col, 
             end_line=end_line, end_col=end_col, title=title) 

 
def error(message, file=None, line=None, col=None, end_line=None, end_col=None, title=None): 
    """A problem. This only logs it; the script still decides its own exit code.""" 
    _command("error", message, file=file, line=line, col=col, 
             end_line=end_line, end_col=end_col, title=title) 


# ----------------------------------------------------------------- groups --- 

@contextmanager 
def group(name): 
    """Collapsible block of log lines. Use with a 'with' statement.""" 
    print(f"::group::{_escape_message(name)}", flush=True) 
    try: 
        yield 
    finally: 
        print("::endgroup::", flush=True) 