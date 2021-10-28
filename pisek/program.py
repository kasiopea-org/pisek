import os
import subprocess
from typing import Optional, List, Any, Dict
from enum import Enum

from . import util
from . import compile


class RunResultKind(Enum):
    """Represents the way the program execution ended. Specially, a program
    that finished successfully, but got Wrong Answer, still gets the OK
    RunResult."""

    OK = 0
    RUNTIME_ERROR = 1
    TIMEOUT = 2


class RunResult:
    def __init__(self, kind: RunResultKind, msg: Optional[str] = None) -> None:
        self.kind: RunResultKind = kind
        self.msg: Optional[str] = msg

    def __repr__(self) -> str:
        return f"RunResult(kind={self.kind}, msg={self.msg})"


def completed_process_to_run_result(result: subprocess.CompletedProcess, executable):
    if result.returncode == 0:
        return RunResult(RunResultKind.OK)
    else:
        error_message = f"Program {os.path.basename(executable)} skončil"
        if result.returncode < 0:
            error_message += f" kvůli signálu {-result.returncode}"
            if result.returncode == -11:
                error_message += " (segmentation fault, přístup mimo povolenou paměť)"
        else:
            error_message += f" s exitcodem {result.returncode}"

        return RunResult(
            RunResultKind.RUNTIME_ERROR,
            error_message + "\n" + util.quote_process_output(result),
        )


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
                return RunResult(RunResultKind.TIMEOUT, f"Timeout po {timeout}s")

        # Because we used `stdout=outp`, the stdout is not available in `result`.
        # Manually add back its head so that it's available in the error message.
        with open(output_file, "r") as outp:
            result.stdout = (
                f"[celý stdout je v {os.path.relpath(output_file)}]\n" + outp.read(3000)
            ).encode("utf-8")

        return completed_process_to_run_result(result, executable)


def run_direct(executable: str, args: List[str]) -> RunResult:
    """like run(), but with no redirections or timeout"""
    result = subprocess.run([executable] + args)

    return completed_process_to_run_result(result, executable)


class Program:
    def __init__(
        self, task_dir: str, name: str, compiler_args: Optional[Dict] = None
    ) -> None:
        self.task_dir: str = task_dir
        self.name: str = os.path.splitext(name)[0]
        self.compiler_args = compiler_args
        self.executable: Optional[str] = None
        basename: Optional[str] = util.resolve_extension(self.task_dir, self.name)
        self.filename: Optional[str] = (
            os.path.join(self.task_dir, basename) if basename is not None else None
        )

    def compile(self) -> None:
        if self.filename is None:
            raise RuntimeError(
                f"Zdrojový kód pro program {self.name} ve složce {self.task_dir} neexistuje"
            )
        self.executable = compile.compile(
            self.filename,
            build_dir=util.get_build_dir(self.task_dir),
            compiler_args=self.compiler_args,
        )
        if self.executable is None:
            raise RuntimeError(f"Program {self.name} se nepodařilo zkompilovat")

    def compile_if_needed(self) -> None:
        # XXX: Only checks for mtime, so may refuse to recompile even if needed
        # (e. g., the CFLAGS changed).
        if self.executable:
            return

        if self.filename is None:
            raise RuntimeError(
                f"Zdrojový kód pro program {self.name} ve složce {self.task_dir} neexistuje"
            )
        executable = compile.compile(
            self.filename, build_dir=util.get_build_dir(self.task_dir), dry_run=True
        )
        if executable is None:
            raise RuntimeError(f"Program {self.name} se nepodařilo zkompilovat")

        if util.file_is_newer(executable, self.filename):
            self.executable = executable
        else:
            self.compile()

    def run(self, args=None) -> RunResult:
        if args is None:
            args = []

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
