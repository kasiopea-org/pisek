import os
from typing import Dict, Optional
import subprocess

from pisek.env import Env
from pisek.tests.jobs import State, Job, JobManager
from pisek.tests.parts.task_job import TaskJob

import pisek.util as util
import pisek.compile as compile

class ProgramJob(TaskJob):
    def __init__(self, name: str, program: str, env: Env) -> None:
        self.program = program
        self.executable = None
        super().__init__(name, env)

    def _compile(self, compiler_args : Optional[Dict] = None):
        if not self._file_exists(self.program):
            self.fail(f"Program {self.program} does not exist")
            return False
        self.executable = compile.compile(
            self.program,
            build_dir=util.get_build_dir(self._env.task_dir),
            compiler_args=compiler_args,
        )
        if self.executable is None:
            self.fail(f"Program {self.program} could not be compiled.")
            return False
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

    def _get_executable(self) -> str:
        name = os.path.splitext(os.path.split(self.program)[1])[0]
        return os.path.normpath(os.path.join(util.get_build_dir(self._env.task_dir), name))

    def _run_raw(self, args, **kwargs):
        self._access_file(args[0])
        if 'stdin' in kwargs:
            self._access_file(kwargs['stdin'])
            kwargs['stdin'] = open(kwargs['stdin'], "r")
        if 'stdout' in kwargs:
            self._access_file(kwargs['stdout'])
            kwargs['stdout'] = open(kwargs['stdout'], "w")
        return subprocess.run(args, **kwargs)

    def _run_program(self, add_args, **kwargs):
        self._load_compiled()
        return self._run_raw([self.executable] + add_args, **kwargs)


class Compile(ProgramJob):
    def __init__(self, program: str, env: Env) -> None:
        super().__init__(
            name=f"Compile {program}",
            program=program,
            env=env
        )

    def _run(self):
        self._compile()
