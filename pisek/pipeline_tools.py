from datetime import datetime
import os
import sys
from typing import Callable, Optional, Any

from pisek.terminal import eprint, tab, colored
from pisek.task_config import load_config
from pisek.env import Env
from pisek.jobs.cache import Cache

PATH = "."

LOCKED = False
LOCK_FILE = ".pisek_lock"


def run_pipeline(path, pipeline, **env_args):
    env = load_env(path, **env_args)
    if env is None:
        return 1
    pipeline = pipeline(env.fork())
    return pipeline.run_jobs(Cache(env), env)


def load_env(
    path,
    subcommand: Optional[str] = None,
    target: Optional[str] = None,
    solution: Optional[str] = None,
    full: bool = False,
    all_inputs: bool = False,
    skip_on_timeout: bool = False,
    plain: bool = False,
    no_jumps: bool = False,
    no_colors: bool = False,
    strict: bool = False,
    testing_log: bool = False,
    clean: bool = False,
    solutions: Optional[list[str]] = None,
    timeout: Optional[float] = None,
    inputs: int = 5,
):
    config = load_config(path)
    if config is None:
        return None

    if solutions is None:
        solutions = config.solutions.keys()
    else:
        for solution in solutions:
            if solution not in config.solutions:
                solutions_list = "\n".join(config.solutions.keys())
                eprint(
                    f"Unknown solution '{solution}'. Known solutions are:\n{tab(solutions_list)}"
                )
                return None

    env = Env(
        task_dir=path,
        target=target,
        config=config,
        full=full,
        no_jumps=plain or no_jumps,
        no_colors=plain or no_colors,
        strict=strict,
        testing_log=testing_log,
        solutions=solutions,
        timeout=timeout,
        inputs=inputs,
        skip_on_timeout=skip_on_timeout,
        all_inputs=all_inputs or testing_log,
    )

    if config.check_todos():
        if env.strict:
            eprint(colored("Unsolved TODOs in config.", env, "red"))
            return None
        else:
            eprint(colored("Warning: Unsolved TODOs in config", env, "yellow"))

    return env


class Lock:
    def __init__(self, path):
        self._lock_file = os.path.join(path, LOCK_FILE)
        self._locked = False

    def __enter__(self):
        if os.path.exists(self._lock_file):
            eprint("Another pisek instance running in same directory.")
            sys.exit(2)

        with open(self._lock_file, "w") as f:
            f.write(f"Locked by pisek at {datetime.now()}")
        self._locked = True

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self._locked and os.path.exists(self._lock_file):
            os.unlink(self._lock_file)


def locked_folder(f):
    def g(*args, **kwargs):
        with Lock(PATH):
            res = f(*args, **kwargs)
        return res

    return g
