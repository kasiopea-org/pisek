from typing import Optional

from pisek.util import eprint
from pisek.terminal import tab, colored
from pisek.task_config import TaskConfig
from pisek.env import Env
from pisek.jobs.cache import Cache

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
        plain: bool = False,
        strict: bool = False,
        clean: bool = False,
        no_checker: bool = False,
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

    env = Env(
        task_dir=path,
        config=config,
        full=full,
        plain=plain,
        strict=strict,
        no_checker=no_checker,
        solutions=solutions,
        timeout=timeout,
        inputs=inputs,
    )

    if config.check_todos():
        if env.strict:
            eprint(colored("Unsolved TODOs in config.", env, 'red'))
            return None
        else:
            eprint(colored("Warning: Unsolved TODOs in config", env, 'yellow'))

    return env
