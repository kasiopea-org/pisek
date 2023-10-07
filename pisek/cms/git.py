from . import util


def run(command):
    return util.run_and_capture(f"git {command}")


def is_synchronized(allow_ahead=True):
    run("fetch origin")
    local = run("rev-parse @")
    upstream = run("rev-parse origin")
    base = run("merge-base @ origin")
    good = False
    good |= local == upstream
    if allow_ahead:
        good |= upstream == base
    return good


def no_local_changes():
    """TODO"""
    return True


def repo_root():
    return run("rev-parse --show-toplevel")
