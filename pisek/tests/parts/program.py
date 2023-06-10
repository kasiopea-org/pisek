import os
import re
from typing import Dict, Optional
import subprocess

from pisek.env import Env
from pisek.tests.jobs import State, Job, JobManager
from pisek.tests.parts.task_job import TaskJob

import pisek.util as util
import pisek.compile as compile

BUILD_DIR = "build/"

class ProgramJob(TaskJob):
    def __init__(self, name: str, program: str, env: Env) -> None:
        self.program = program
        self.executable = None
        super().__init__(name, env)

    def _compile(self, compiler_args : Optional[Dict] = None):
        program = self._resolve_extension(self.program)
        self.executable = compile.compile(
            program,
            build_dir=self._get_build_dir(),
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

    def _run_raw(self, args, **kwargs):
        self._access_file(args[0])
        if 'stdin' in kwargs and isinstance(kwargs['stdin'], str):
            kwargs['stdin'] = self._open_file(kwargs['stdin'], "r")
        if 'stdout' in kwargs and isinstance(kwargs['stdout'], str):
            kwargs['stdout'] = self._open_file(kwargs['stdout'], "w")
        return subprocess.run(args, **kwargs)

    def _run_program(self, add_args, **kwargs):
        self._load_compiled()
        return self._run_raw([self.executable] + add_args, **kwargs)
        
    def _get_build_dir(self) -> str:
        return os.path.normpath(os.path.join(self._env.task_dir, BUILD_DIR))
    
    def _get_executable(self) -> str:
        name = os.path.basename(self.program)
        return os.path.normpath(os.path.join(util.get_build_dir(self._env.task_dir), name))

    def _resolve_extension(self, name: str) -> str:
        """
        Given `name`, finds a file named `name`.[ext],
        where [ext] is a file extension for one of the supported languages.

        If a name with a valid extension is given, it is returned unchanged
        """
        extensions = compile.supported_extensions()
        candidates = []
        for name in [name, self._name_without_expected_score(name)]:
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
                f"No file with given name exists: {name}"
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
