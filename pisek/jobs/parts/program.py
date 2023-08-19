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
from pisek.terminal import tab, colored
from pisek.jobs.parts.task_job import TaskJob

import pisek.util as util

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
    def _format(text: str, env: Env, chars: int = 1500, lines: int = 20):
        res = ""
        i = 0
        for char in text:
            res += char
            lines -= (char == '\n')
            if lines <= 0 or len(res) >= chars:
                break
        res = tab(res)
        if colored:
            res = colored(res, env, 'yellow')
        return res

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

    def stdout(self, env: Env):
        if self.stdout_file:
            return f" in file {self.stdout_file}:\n" + self._format(self.raw_stdout(), env)
        else:
            return " has been discarded"

    def stderr(self, env: Env):
        text = self._format(self.raw_stderr(), env)
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
                 env={}, print_stderr: bool = False) -> RunResult:
        """Runs args as a command."""
        executable = args[0]
        self._access_file(executable)

        minibox_args = []

        minibox_args.append(f"--time={timeout}")
        minibox_args.append(f"--wall-time={timeout}")
        minibox_args.append(f"--mem={mem}")
        minibox_args.append(f"--processes={processes}")

        minibox_args.append(f"--stdin={os.path.abspath(stdin) if stdin else '/dev/null'}")
        minibox_args.append(f"--stdout={os.path.abspath(stdout) if stdout else '/dev/null'}")
        if stderr:
            minibox_args.append(f"--stderr={os.path.abspath(stderr)}")

        for key, val in env.items():
            minibox_args.append(f"--env={key}={val}")

        minibox_args.append(f"--silent")
        minibox_args.append(f"--meta=-")

        process = subprocess.Popen(
            [self._executable("minibox")] + minibox_args + ["--run", "--"] + args,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if print_stderr:
            stderr_raw = ""
            while True:
                line = process.stderr.read().decode()
                if not line:
                    break
                stderr_raw += line
                print(colored(line, self._env, 'yellow'), end="", file=sys.stderr)
                self.dirty = True

        process.wait()

        meta_raw = process.stdout.read().decode().strip().split('\n')
        meta = {key: val for key, val in map(lambda x: x.split(":", 1), meta_raw)}

        if not print_stderr:
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

    def _program_fail(self, msg: str, res: RunResult):
        """Fail that nicely formats RunResult"""
        self._fail(f"{msg}\n{tab(self._quote_program(res))}")

    def _quote_program(self, res: RunResult):
        """Quotes program's stdout and stderr."""
        program_msg = ""
        for std in ('stdout', 'stderr'):
            program_msg += f"{std}{getattr(res, std)(self._env)}\n"
        return program_msg[:-1]
