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
    stdout: Optional[str] = None
    stderr: Optional[str] = None

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
    stdout = result.stdout.decode("utf-8") if result.stdout is not None else result.stdout
    stderr = result.stderr.decode("utf-8") if result.stderr is not None else result.stderr
    if result.returncode == 0:
        return RunResult(RunResultKind.OK, 0, stdout, stderr)
    else:
        return RunResult(RunResultKind.RUNTIME_ERROR, result.returncode, stdout, stderr)


class ProgramJob(TaskJob):
    def __init__(self, name: str, program: str, env: Env) -> None:
        self.program = program
        self.executable = None
        super().__init__(name, env)

    def _compile(self, compiler_args : Optional[Dict] = None):
        program = self._resolve_extension(self.program)
        if program is None:
            return False

        result = compile.compile(
            program,
            build_dir=self._executable("."),
            compiler_args=compiler_args,
        )
        if result is not None:
            self.fail(f"Program {self.program} could not be compiled: {tab(result)}")
            return False
        if not self._load_compiled():
            return False

        self._access_file(program)
        self._access_file(self.executable)

        return True
    
    def _load_compiled(self) -> bool:
        program_name = os.path.basename(self.program)
        for name in [program_name, self._name_without_expected_score(program_name)]:
            self.executable = self._executable(name)
            if not os.path.exists(self.executable):  # No caching here is intentional
                continue
            return True
        
        return self.fail(
            f"Program {self.name} does not exist, "
            f"although it should have been compiled already."
        )

    def _run_raw(self, args, timeout: Optional[float] = None, **kwargs) -> RunResult:
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
            return RunResult(RunResultKind.TIMEOUT, -1, f"Timeout po {timeout}s")
        finally:
            for stream in opened:
                stream.close()
        return completed_process_to_run_result(result)

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

    def _program_fail(self, msg: str, res: RunResult):
        program_msg = ""
        for std in ('stdout', 'stderr'):
            program_msg += f"{std}:"
            text = getattr(res, std)
            if text:
                program_msg += "\n" + util.quote_output(text)
            else:
                program_msg += " (none)"
            program_msg += "\n"
        self.fail(f"{msg}\n{program_msg}")

class Compile(ProgramJob):
    def __init__(self, program: str, env: Env, compile_args: Dict = {}) -> None:
        self._compile_args = compile_args
        super().__init__(
            name=f"Compile {os.path.basename(program)}",
            program=program,
            env=env
        )

    def _run(self):
        return self._compile(self._compile_args)
