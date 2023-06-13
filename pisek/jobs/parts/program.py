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
from pisek.jobs.parts.task_job import TaskJob

import pisek.util as util
import pisek.compile as compile

class RunResultKind(Enum):
    """Represents the way the program execution ended. Specially, a program
    that finished successfully, but got Wrong Answer, still gets the OK
    RunResult."""

    OK = 0
    RUNTIME_ERROR = 1
    TIMEOUT = 2

@dataclass
class RunResult():
    kind: RunResultKind
    returncode: int
    msg: Optional[str] = None

def run_result_representer(dumper, run_result):
    return dumper.represent_sequence(u'!RunResult', [run_result.kind.name, run_result.returncode, run_result.msg])

def run_result_constructor(loader, value):
    kind, returncode, msg = loader.construct_sequence(value)
    return RunResult(RunResultKind[kind], returncode, msg)

yaml.add_representer(RunResult, run_result_representer)
yaml.add_constructor(u'!RunResult', run_result_constructor)


def completed_process_to_run_result(result: subprocess.CompletedProcess, executable) -> RunResult:
    if result.returncode == 0:
        return RunResult(RunResultKind.OK, 0, util.quote_process_output(result))
    else:
        error_message = f"Program {os.path.basename(executable)} ended"
        if result.returncode < 0:
            error_message += f" because of signal {-result.returncode}"
            if result.returncode == -11:
                error_message += " (segmentation fault, access outside of own memory)"
        else:
            error_message += f" with exitcode {result.returncode}"

        return RunResult(
            RunResultKind.RUNTIME_ERROR,
            result.returncode,
            error_message + "\n" + util.quote_process_output(result),
        )


class ProgramJob(TaskJob):
    def __init__(self, name: str, program: str, env: Env) -> None:
        self.program = program
        self.executable = None
        super().__init__(name, env)

    def _compile(self, compiler_args : Optional[Dict] = None):
        program = self._resolve_extension(self.program)
        if program is None:
            return False

        self.executable = compile.compile(
            program,
            build_dir=self._executable("."),
            compiler_args=compiler_args,
        )
        if self.executable is None:
            self.fail(f"Program {self.program} could not be compiled.")
            return False
        self._access_file(program)
        self._access_file(self.executable)

        return True
    
    def _load_compiled(self) -> bool:
        executable = self._get_executable()
        if not self._file_exists(executable):
            self.fail(
                f"Program {self.executable} does not exist, "
                f"although it should have been compiled already."
            )
            return False
        self.executable = executable
        return True

    def _run_raw(self, args, timeout: float = DEFAULT_TIMEOUT, **kwargs) -> RunResult:
        executable = args[0]
        self._access_file(executable)
        for std, mode in [('stdin', 'r'), ('stdout', 'w'), ('stderr', 'w')]:
            if std in kwargs and isinstance(kwargs[std], str):
                kwargs[std] = self._open_file(kwargs[std], mode)
            else:
                kwargs[std] = subprocess.PIPE
        
        try:
            result = subprocess.run(args, timeout=timeout, **kwargs)
        except subprocess.TimeoutExpired:
            return RunResult(RunResultKind.TIMEOUT, -1, f"Timeout po {timeout}s")
        return completed_process_to_run_result(result, executable)

    def _run_program(self, add_args, **kwargs) -> Optional[RunResult]:
        if not self._load_compiled():
            return None
        return self._run_raw([self.executable] + add_args, **kwargs)
 
    def _get_executable(self) -> str:
        return self._executable(os.path.basename(self.program))

    def _resolve_extension(self, name: str) -> str:
        """
        Given `name`, finds a file named `name`.[ext],
        where [ext] is a file extension for one of the supported languages.

        If a name with a valid extension is given, it is returned unchanged
        """
        extensions = compile.supported_extensions()
        candidates = []
        candidate_names = [name, self._name_without_expected_score(name)]
        for name in candidate_names: 
            for ext in extensions:
                if os.path.isfile(name + ext):
                    candidates.append(name + ext)
                if name.endswith(ext) and os.path.isfile(name):
                    # Extension already present in `name`
                    candidates.append(name)
            if len(candidates):
                break
        
        if len(candidates) == 0:
            return self.fail(
                f"No file with given name exists: {' or '.join(map(os.path.basename, candidate_names))}"
            )
        if len(candidates) > 1:
            return self.fail(
                f"Multiple files with same name exist: {', '.join(candidates)}"
            )

        return candidates[0]

    def _name_without_expected_score(self, name: str):
        match = re.fullmatch(r"(.*?)_([0-9]{1,3}|X)b", name)
        if match:
            return match[1]
        return name


class Compile(ProgramJob):
    def __init__(self, program: str, env: Env) -> None:
        super().__init__(
            name=f"Compile {os.path.basename(program)}",
            program=program,
            env=env
        )

    def _run(self):
        self._compile()
