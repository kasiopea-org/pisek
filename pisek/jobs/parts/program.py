from dataclasses import dataclass
from enum import Enum
import os
import re
import sys
from typing import Dict, Optional
import subprocess
import yaml

from pisek.task_config import DEFAULT_TIMEOUT
from pisek.env import Env
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.status import tab
from pisek.jobs.parts.task_job import TaskJob

import pisek.util as util
import pisek.compile as compile

class RunResultKind(Enum):
    OK = 0
    RUNTIME_ERROR = 1
    TIMEOUT = 2

class RunResult():
    """Represents the way the program execution ended. Specially, a program
    that finished successfully, but got Wrong Answer, still gets the OK
    RunResult."""
    def __init__(self, kind: RunResultKind, returncode: int,
                 stdout_file=None, stderr_file=None, stderr_text=None):
        self.kind = kind
        self.returncode = returncode
        self.stdout_file = stdout_file
        self.stderr_file = stderr_file
        self.stderr_text = stderr_text

    @staticmethod
    def _format(text, chars=1500, lines=20):
        res = ""
        i = 0
        for char in text:
            res += char
            lines -= (char == '\n')
            if lines <= 0 or len(res) >= chars:
                break
        return tab(res)
    def raw_stdout(self):
        if self.stdout_file:
            return open(self.stdout_file).read()
        else:
            return None

    def raw_stderr(self):
        if self.stderr_file:
            return open(self.stderr_file).read()
        else:
            return self.stderr_text

    def stdout(self):
        if self.stdout_file:
            return f" in file {self.stdout_file}:\n" + self._format(self.raw_stdout())
        else:
            return " has been discarded"

    def stderr(self):
        text = tab(self._format(self.raw_stderr()))
        if self.stderr_file:
            return f" in file {self.stderr_file}:\n{text}"
        else:
            return f":\n{text}"


def run_result_representer(dumper, run_result: RunResult):
    return dumper.represent_sequence(
        u'!RunResult', [
            run_result.kind.name,
            run_result.returncode,
            run_result.stdout_file,
            run_result.stderr_file,
            run_result.stderr_text
        ]
    )

def run_result_constructor(loader, value):
    kind, returncode, out_f, err_f, err_t = loader.construct_sequence(value)
    return RunResult(RunResultKind[kind], returncode, out_f, err_f, err_t)

yaml.add_representer(RunResult, run_result_representer)
yaml.add_constructor(u'!RunResult', run_result_constructor)


def completed_process_to_run_result(result: subprocess.CompletedProcess) -> RunResult:
    stdout = result.stdout.decode("utf-8") if result.stdout is not None else ""
    stderr = result.stderr.decode("utf-8") if result.stderr is not None else ""
    if result.returncode == 0:
        return RunResult(RunResultKind.OK, 0, stdout, stderr)
    else:
        return RunResult(RunResultKind.RUNTIME_ERROR, result.returncode, stdout, stderr)


class ProgramJob(TaskJob):
    """Job that deals with a program."""
    def _init(self, name: str, program: str) -> None:
        self.program = program
        self.executable : Optional[str] = None
        super()._init(name)

    def _compile(self, compiler_args : Optional[Dict] = None):
        """Compiles program."""
        program = self._resolve_extension(self.program)
        if program is None:
            return False

        result = compile.compile(
            program,
            build_dir=self._executable("."),
            compiler_args=compiler_args,
        )
        if result is not None:
            self._fail(f"Program {self.program} could not be compiled: {tab(result)}")
            return False
        if not self._load_compiled():
            return False

        self._access_file(program)
        self._access_file(self.executable)

        return True

    def _load_compiled(self) -> bool:
        """Loads name of compiled program."""
        self.executable = self._executable(os.path.basename(self.program))
        if not self._file_exists(self.executable):
            self._fail(
                f"Program {self.name} does not exist, "
                f"although it should have been compiled already."
            )
            return False
        return True


    def _run_raw(self, args, timeout: float = DEFAULT_TIMEOUT, mem: int = 0,
                 processes: int = 4, stdin: Optional[str] = None,
                 stdout: Optional[str] = None, stderr: Optional[str] = None,
                 env={}) -> RunResult:
        """Runs args as a command."""
        executable = args[0]
        self._access_file(executable)

        minibox_args = []

        minibox_args.append(f"--time={timeout}")
        minibox_args.append(f"--wall-time={timeout}")
        minibox_args.append(f"--mem={mem}")
        minibox_args.append(f"--processes={processes}")

        minibox_args.append(f"--stdin={stdin if stdin else '/dev/null'}")
        minibox_args.append(f"--stdout={stdout if stdout else '/dev/null'}")
        if stderr:
            minibox_args.append(f"--stderr={stderr}")

        for key, val in env.items():
            minibox_args.append(f"--env={key}={val}")

        minibox_args.append(f"--silent")
        minibox_args.append(f"--meta=-")

        process = subprocess.Popen(
            [self._executable("minibox")] + minibox_args + ["--run", "--"] + args,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        process.wait()

        meta_raw = process.stdout.read().decode().strip().split('\n')
        meta = {key: val for key, val in map(lambda x: x.split(":", 1), meta_raw)}

        stderr_raw =  process.stderr.read().decode()
        stderr_text = None if stderr else stderr_raw
        if process.returncode == 0:
            return RunResult(RunResultKind.OK, 0, stdout, stderr, stderr_text)
        elif process.returncode == 1:
            if meta['status'] in ('RE', 'SG'):
                rc = int(re.search('\d+', meta['message'])[0])
                return RunResult(RunResultKind.RUNTIME_ERROR, rc, stdout, stderr, stderr_text)
            elif meta['status'] == 'TO':
                return RunResult(RunResultKind.TIMEOUT, -1, stdout, stderr, f"[Timeout after {timeout}s]")
        else:
            self._fail(f"Minibox error:\n{tab(stderr_raw)}")

    def _run_program(self, add_args, **kwargs) -> Optional[RunResult]:
        """Runs program."""
        if not self._load_compiled():
            return None
        return self._run_raw([self.executable] + add_args, **kwargs)

    def _get_executable(self) -> str:
        """Get a name of a compiled program."""
        return self._executable(os.path.basename(self.program))

    def _resolve_extension(self, name: str) -> Optional[str]:
        """
        Given `name`, finds a file named `name`.[ext],
        where [ext] is a file extension for one of the supported languages.

        If a name with a valid extension is given, it is returned unchanged
        """
        extensions = compile.supported_extensions()
        candidates = []
        for ext in extensions:
            if os.path.isfile(name + ext):
                candidates.append(name + ext)
            if name.endswith(ext) and os.path.isfile(name):
                # Extension already present in `name`
                candidates.append(name)

        if len(candidates) == 0:
            self._fail(
                f"No file with given name exists: {name}"
            )
            return None
        if len(candidates) > 1:
            self._fail(
                f"Multiple files with same name exist: {', '.join(candidates)}"
            )
            return None
        return candidates[0]

    def _program_fail(self, msg: str, res: RunResult):
        """Fail that nicely formats RunResult"""
        self._fail(f"{msg}\n{tab(self._quote_program(res))}")

    def _quote_program(self, res: RunResult):
        """Quotes program's stdout and stderr."""
        program_msg = ""
        for std in ('stdout', 'stderr'):
            program_msg += f"{std}{getattr(res, std)()}\n"
        return program_msg[:-1]

class Compile(ProgramJob):
    """Job that compiles a program."""
    def _init(self, program: str, compile_args: Dict = {}) -> None:
        self._compile_args = compile_args
        super()._init(f"Compile {os.path.basename(program)}", program)

    def _run(self):
        return self._compile(self._compile_args)
