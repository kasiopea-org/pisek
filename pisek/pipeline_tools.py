from datetime import datetime
import os
import sys
from typing import Callable, Optional, Any

from pisek.terminal import eprint, tab, colored
from pisek.task_config import TaskConfig
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
    strict: bool = False,
    clean: bool = False,
    solutions: Optional[list[str]] = None,
    timeout: Optional[float] = None,
    inputs: int = 5,
):
    config = TaskConfig()
    err = config.load(path)
    if err:
        eprint(f"Error when loading config:\n{tab(err)}")
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
        plain=plain,
        strict=strict,
        solutions=solutions,
        timeout=timeout,
        inputs=inputs,
        skip_on_timeout=skip_on_timeout,
        all_inputs=all_inputs,
    )

    if config.check_todos():
        if env.strict:
            eprint(colored("Unsolved TODOs in config.", env, "red"))
            return None
        else:
            eprint(colored("Warning: Unsolved TODOs in config", env, "yellow"))

    return env


def lock_folder(path: str):
    global LOCKED
    file = os.path.join(path, LOCK_FILE)
    if os.path.exists(file):
        eprint("Another pisek instance running in same directory.")
        sys.exit(2)
    with open(file, "w") as f:
        f.write(f"Locked by pisek at {datetime.now()}")
    LOCKED = True


def unlock_folder(path: str):
    global LOCKED
    file = os.path.join(path, LOCK_FILE)
    if LOCKED and os.path.exists(file):
        os.unlink(file)
    LOCKED = False


def locked_folder(f):
    def g(*args, **kwargs):
        lock_folder(PATH)
        res = f(*args, **kwargs)
        unlock_folder(PATH)
        return res

    return g
