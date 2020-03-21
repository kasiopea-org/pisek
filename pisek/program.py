import os
import subprocess
from typing import Optional, List
from enum import Enum

from . import util
from . import compile


class RunResult(Enum):
    OK = 0
    NONZERO_EXIT_CODE = 1
    TIMEOUT = 2
    WRONG_ANSWER = 3
    # ^ cannot be returned by run(), is returned by the judge


def run(
    executable: str,
    input_file: str,
    output_file: str,
    timeout: int = util.DEFAULT_TIMEOUT,
) -> RunResult:
    # TODO: Adapt the code from https://gist.github.com/s3rvac/f97d6cbdfdb15c0a32e7e941f7f4a3fa
    #       to limit the memory of the subprocess
    with open(input_file, "r") as inp:
        with open(output_file, "w") as outp:
            try:
                result = subprocess.run(
                    executable,
                    stdin=inp,
                    stdout=outp,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return RunResult.TIMEOUT

            if result.returncode == 0:
                return RunResult.OK
            else:
                return RunResult.NONZERO_EXIT_CODE


def run_direct(executable: str, args: List[str] = []) -> RunResult:
    """ like run(), but with no redirections or timeout """
    result = subprocess.run([executable] + args)

    if result.returncode == 0:
        return RunResult.OK
    else:
        return RunResult.NONZERO_EXIT_CODE


class Program:
    def __init__(self, task_dir: str, name: str) -> None:
        self.task_dir: str = task_dir
        self.name: str = name
        self.executable: Optional[str] = None

    def compile(self) -> None:
        filename = util.resolve_extension(self.task_dir, self.name)
        if filename is None:
            raise RuntimeError(
                f"Program {self.name} ve složce {self.task_dir} neexistuje"
            )
        self.executable = compile.compile(os.path.join(self.task_dir, filename))
        if self.executable is None:
            raise RuntimeError(f"Program {self.name} se nepodařilo zkompilovat")

    def compile_if_needed(self) -> None:
        # TODO: we could avoid recompiling if the binary exists and is fresh
        if not self.executable:
            self.compile()

    def run(self, args: List[str] = []) -> RunResult:
        self.compile_if_needed()
        assert self.executable is not None
        return run_direct(self.executable, args)
