import os
import subprocess
from typing import Optional, List

from . import util
from . import compile


def run(executable: str, input_file: str, output_file: str, timeout: int = 100) -> bool:
    # TODO: Adapt the code from https://gist.github.com/s3rvac/f97d6cbdfdb15c0a32e7e941f7f4a3fa
    #       to limit the memory of the subprocess
    with open(input_file, "r") as inp:
        with open(output_file, "w") as outp:
            result = subprocess.run(
                executable,
                stdin=inp,
                stdout=outp,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )

            return result.returncode == 0


def run_direct(executable: str, args: List[str] = []) -> bool:
    """ like run(), but with no redirections or timeout """
    result = subprocess.run([executable] + args)

    return result.returncode == 0


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

    def run(self, args: List[str] = []) -> bool:
        self.compile_if_needed()
        assert self.executable is not None
        return run_direct(self.executable, args)
