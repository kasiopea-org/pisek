# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from dataclasses import dataclass
from enum import Enum
import os
import re
import sys
from typing import Optional
import subprocess
import yaml

from pisek.task_config import DEFAULT_TIMEOUT
from pisek.env import Env
from pisek.jobs.jobs import PipelineItemFailure
from pisek.terminal import tab, colored
from pisek.jobs.parts.task_job import TaskHelper, TaskJob

import pisek.util as util


class RunResultKind(Enum):
    OK = 0
    RUNTIME_ERROR = 1
    TIMEOUT = 2


class RunResult:
    """Represents the way the program execution ended. Specially, a program
    that finished successfully, but got Wrong Answer, still gets the OK
    RunResult."""

    def __init__(
        self,
        kind: RunResultKind,
        returncode: int,
        time: float,
        wall_time: float,
        stdout_file: Optional[str] = None,
        stderr_file: Optional[str] = None,
        stderr_text: Optional[str] = None,
        status: str = "",
    ):
        self.kind = kind
        self.returncode = returncode
        self.stdout_file = stdout_file
        self.stderr_file = stderr_file
        self.stderr_text = stderr_text
        self.status = status
        self.time = time
        self.wall_time = wall_time

    @staticmethod
    def _format(text: str, env: Env, max_lines: int = 20, max_chars: int = 100):
        res = tab(TaskHelper._short_text(text, max_lines, max_chars))
        if not env.plain:
            res = colored(res, env, "yellow")
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
            return f" in file {self.stdout_file}:\n" + self._format(
                self.raw_stdout(), env
            )
        else:
            return " has been discarded"

    def stderr(self, env: Env):
        text = self._format(self.raw_stderr(), env)
        if self.stderr_file:
            return f" in file {self.stderr_file}:\n{text}"
        else:
            return f":\n{text}"

    def __str__(self):
        return f"<RunResult {self.kind.name}, exitcode: {self.returncode}>"

    __repr__ = __str__


def run_result_representer(dumper, run_result: RunResult):
    return dumper.represent_sequence(
        "!RunResult",
        [
            run_result.kind.name,
            run_result.returncode,
            run_result.time,
            run_result.wall_time,
            run_result.stdout_file,
            run_result.stderr_file,
            run_result.stderr_text,
            run_result.status,
        ],
    )


def run_result_constructor(loader, value):
    (
        kind,
        returncode,
        time,
        wall_time,
        out_f,
        err_f,
        err_t,
        status,
    ) = loader.construct_sequence(value)
    return RunResult(
        RunResultKind[kind], returncode, time, wall_time, out_f, err_f, err_t, status
    )


yaml.add_representer(RunResult, run_result_representer)
yaml.add_constructor("!RunResult", run_result_constructor)


class ProgramJob(TaskJob):
    """Job that deals with a program."""

    def __init__(self, env: Env, name: str, program: str) -> None:
        super().__init__(env, name)
        self.program = program
        self.executable: Optional[str] = None

    def _load_compiled(self) -> None:
        """Loads name of compiled program."""
        self.executable = self._executable(os.path.basename(self.program))
        if not self._file_exists(self.executable):
            raise PipelineItemFailure(
                f"Program {self.name} does not exist, "
                f"although it should have been compiled already."
            )

    def _run_raw(
        self,
        args,
        timeout: float = DEFAULT_TIMEOUT,
        mem: int = 0,
        processes: int = 1,
        stdin: Optional[str] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        env={},
        print_stderr: bool = False,
    ) -> RunResult:
        """Runs args as a command."""
        executable = args[0]
        self._access_file(executable)

        minibox_args = []

        minibox_args.append(f"--time={timeout}")
        minibox_args.append(f"--wall-time={timeout}")
        minibox_args.append(f"--mem={mem}")
        minibox_args.append(f"--processes={processes}")

        if stdin:
            self._access_file(stdin)
        if stdout:
            self._access_file(stdout)
        minibox_args.append(
            f"--stdin={os.path.abspath(stdin) if stdin else '/dev/null'}"
        )
        minibox_args.append(
            f"--stdout={os.path.abspath(stdout) if stdout else '/dev/null'}"
        )
        if stderr:
            self._access_file(stderr)
            minibox_args.append(f"--stderr={os.path.abspath(stderr)}")

        for key, val in env.items():
            minibox_args.append(f"--env={key}={val}")

        minibox_args.append(f"--silent")
        minibox_args.append(f"--meta=-")

        process = subprocess.Popen(
            [self._executable("minibox")] + minibox_args + ["--run", "--"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Mypy
        if process.stdout is None:
            raise RuntimeError(f"Captured stdout of {process} should not be None")
        if process.stderr is None:
            raise RuntimeError(f"Captured stderr of {process} should not be None")

        if print_stderr:
            stderr_raw = ""
            while True:
                line = process.stderr.read().decode()
                if not line:
                    break
                stderr_raw += line
                self._print(colored(line, self._env, "yellow"), end="", stderr=True)

        process.wait()

        meta_raw = process.stdout.read().decode().strip().split("\n")
        meta = {key: val for key, val in map(lambda x: x.split(":", 1), meta_raw)}
        if not print_stderr:
            stderr_raw = process.stderr.read().decode()
        stderr_text = None if stderr else stderr_raw
        if process.returncode == 0:
            t, wt = float(meta["time"]), float(meta["time-wall"])
            return RunResult(
                RunResultKind.OK,
                0,
                t,
                wt,
                stdout,
                stderr,
                stderr_text,
                "Finished successfully",
            )
        elif process.returncode == 1:
            t, wt = float(meta["time"]), float(meta["time-wall"])
            if meta["status"] in ("RE", "SG"):
                if meta["status"] == "RE":
                    return_code = int(meta["exitcode"])
                elif meta["status"] == "SG":
                    return_code = int(meta["exitsig"])

                return RunResult(
                    RunResultKind.RUNTIME_ERROR,
                    return_code,
                    t,
                    wt,
                    stdout,
                    stderr,
                    stderr_text,
                    meta["message"],
                )
            elif meta["status"] == "TO":
                return RunResult(
                    RunResultKind.TIMEOUT,
                    -1,
                    t,
                    wt,
                    stdout,
                    stderr,
                    stderr_text,
                    f"Timeout after {timeout}s",
                )
            else:
                raise RuntimeError(f"Unknown minibox status {meta['message']}.")
        else:
            raise PipelineItemFailure(f"Minibox error:\n{tab(stderr_raw)}")

    def _run_program(self, add_args, **kwargs) -> RunResult:
        """Runs program."""
        self._load_compiled()
        return self._run_raw([self.executable] + add_args, **kwargs)

    def _get_executable(self) -> str:
        """Get a name of a compiled program."""
        return self._executable(os.path.basename(self.program))

    def _create_program_failure(self, msg: str, res: RunResult):
        """Create PipelineItemFailure that nicely formats RunResult"""
        return PipelineItemFailure(f"{msg}\n{tab(self._quote_program(res))}")

    def _quote_program(self, res: RunResult):
        """Quotes program's stdout and stderr."""
        program_msg = f"status: {res.status}\n"
        for std in ("stdout", "stderr"):
            program_msg += f"{std}{getattr(res, std)(self._env)}\n"
        return program_msg[:-1]
