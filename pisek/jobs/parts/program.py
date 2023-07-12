from dataclasses import dataclass
from enum import Enum
import os
import re
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

@dataclass
class RunResult():
    """Represents the way the program execution ended. Specially, a program
    that finished successfully, but got Wrong Answer, still gets the OK
    RunResul."""
    kind: RunResultKind
    returncode: int
    stdout: str = ""
    stderr: str = ""

def run_result_representer(dumper, run_result: RunResult):
    return dumper.represent_sequence(
        u'!RunResult', [run_result.kind.name, run_result.returncode, run_result.stdout, run_result.stderr]
    )

def run_result_constructor(loader, value):
    kind, returncode, stdout, stderr = loader.construct_sequence(value)
    return RunResult(RunResultKind[kind], returncode, stdout, stderr)

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
        

    def _run_raw(self, args, timeout: Optional[float] = None, **kwargs) -> RunResult:
        """Runs args as a command."""
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        executable = args[0]
        self._access_file(executable)
        opened = []
        for std, mode in [('stdin', 'r'), ('stdout', 'w'), ('stderr', 'w')]:
            if std in kwargs and isinstance(kwargs[std], str):
                kwargs[std] = self._open_file(kwargs[std], mode)
                opened.append(kwargs[std])
            else:
                kwargs[std] = subprocess.PIPE
        
        try:
            result = subprocess.run(args, timeout=timeout, **kwargs)
        except subprocess.TimeoutExpired:
            return RunResult(RunResultKind.TIMEOUT, -1, f"Timeout after {timeout}s")
        finally:
            for stream in opened:
                stream.close()
        return completed_process_to_run_result(result)

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
        self._fail(f"{msg}\n{self._quote_program(res)}")
 
    def _quote_program(self, res: RunResult):
        """Quotes program's stdout and stderr."""
        program_msg = ""
        for std in ('stdout', 'stderr'):
            program_msg += f"{std}:"
            text = getattr(res, std)
            if text:
                program_msg += "\n" + util.quote_output(text)
            else:
                program_msg += " (none)"
            program_msg += "\n"
        return program_msg[:-1]

class Compile(ProgramJob):
    """Job that compiles a program."""
    def _init(self, program: str, compile_args: Dict = {}) -> None:
        self._compile_args = compile_args
        super()._init(f"Compile {os.path.basename(program)}", program)

    def _run(self):
        return self._compile(self._compile_args)
