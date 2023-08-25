import glob
import os
from . import git, util
from pisek import __main__ as pisek_main

### TODO: Nevolat main, je to strašná prasárna!
from pisek.task_config import TaskConfig


def assert_git():
    assert git.is_synchronized(), "Branch is not up-to-date with origin/master"
    assert git.no_local_changes(), "Some local changes exist"


def get_solutions_not_in_config(config):
    # TODO: přepsat na config.solutions_subdir
    return sorted(
        set(os.path.splitext(p)[0] for p in glob.glob("solutions/" + "*"))
        - set(config.solutions)
    )


def instant(args):
    assert_git()
    not_in_config = get_solutions_not_in_config(TaskConfig("."))
    if not_in_config:
        util.warn(
            f"Tato řešení jsou v solutions/, ale ne v configu: {' '.join(not_in_config)}"
        )


def sane(args):
    instant(args)
    config = TaskConfig(".")
    return pisek_main.main(["-c", "test", "solution", config.solutions[0], "--full"])


def thorough(args):
    instant(args)
    return pisek_main.main(["-c", "--strict", "--full"])
