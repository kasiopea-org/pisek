import os
import subprocess
from typing import Optional, List, Any
from enum import Enum

from . import util
from . import compile


class RunResult(Enum):
    """Represents the way the program execution ended. Specially, a program
    that finished successfully, but got Wrong Answer, still gets the OK
    RunResult."""

    OK = 0
    NONZERO_EXIT_CODE = 1
    TIMEOUT = 2


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
        self.name: str = os.path.splitext(name)[0]
        self.executable: Optional[str] = None
        basename: Optional[str] = util.resolve_extension(self.task_dir, self.name)
        self.filename: Optional[str] = os.path.join(
            self.task_dir, basename
        ) if basename is not None else None

    def compile(self) -> None:
        if self.filename is None:
            raise RuntimeError(
                f"Zdrojový kód pro program {self.name} ve složce {self.task_dir} neexistuje"
            )
        self.executable = compile.compile(self.filename)
        if self.executable is None:
            raise RuntimeError(f"Program {self.name} se nepodařilo zkompilovat")

    def compile_if_needed(self) -> None:
        # XXX: Only checks for mtime, so may refuse to recompile even if needed (e. g., the CFLAGS changed).
        if self.executable:
            return

        if self.filename is None:
            raise RuntimeError(
                f"Zdrojový kód pro program {self.name} ve složce {self.task_dir} neexistuje"
            )
        executable = compile.compile(self.filename, True)
        if executable is None:
            raise RuntimeError(f"Program {self.name} se nepodařilo zkompilovat")

        mtime = os.path.getmtime
        exists = os.path.exists
        if (
            exists(executable)
            and exists(self.filename)
            and mtime(executable) > mtime(self.filename)
        ):
            self.executable = executable
            return

        self.compile()

    def run(self, args: List[str] = []) -> RunResult:
        self.compile_if_needed()
        assert self.executable is not None
        return run_direct(self.executable, args)

    def run_raw(
        self, program_args: List[str], *args: Any, **kwargs: Any
    ) -> subprocess.CompletedProcess:
        self.compile_if_needed()
        assert self.executable is not None
        program_args.insert(0, self.executable)
        return subprocess.run(program_args, *args, **kwargs)
