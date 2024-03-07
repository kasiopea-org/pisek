# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from dataclasses import dataclass, field
from enum import Enum
import os
import tempfile
import time
from typing import Optional, Any, Union, Callable
import signal
import subprocess
import yaml

from pisek.env.task_config import ProgramType
from pisek.env.env import Env
from pisek.paths import TaskPath
from pisek.jobs.jobs import PipelineItemFailure
from pisek.utils.text import tab
from pisek.utils.terminal import colored_env
from pisek.jobs.parts.task_job import TaskHelper, TaskJob


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
        stdout_file: Optional[Union[TaskPath, int]] = None,
        stderr_file: Optional[TaskPath] = None,
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
        return colored_env(res, "yellow", env)

    def raw_stdout(self, access_file: Callable[[TaskPath], None]):
        if isinstance(self.stdout_file, TaskPath):
            access_file(self.stdout_file)
            return open(self.stdout_file.path).read()
        else:
            return None

    def raw_stderr(self, access_file: Callable[[TaskPath], None]):
        if isinstance(self.stderr_file, TaskPath):
            access_file(self.stderr_file)
            return open(self.stderr_file.path).read()
        else:
            return self.stderr_text

    def stdout(self, env: Env, access_file: Callable[[TaskPath], None]):
        if isinstance(self.stdout_file, str):
            return f" in file {self.stdout_file}:\n" + self._format(
                self.raw_stdout(access_file), env
            )
        else:
            return " has been discarded"

    def stderr(self, env: Env, access_file: Callable[[TaskPath], None]):
        text = self._format(self.raw_stderr(access_file), env)
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


@dataclass
class ProgramPoolItem:
    executable: TaskPath
    args: list[str]
    time_limit: float
    clock_limit: float
    mem_limit: int
    process_limit: int
    stdin: Optional[Union[TaskPath, int]]
    stdout: Optional[Union[TaskPath, int]]
    stderr: Optional[TaskPath]
    env: dict[str, str] = field(default_factory=lambda: {})

    def to_popen(self, minibox: str, meta_file: str) -> dict[str, Any]:
        """Returns subprocess.Popen args for executing this PoolItem."""
        result: dict[str, Any] = {}

        minibox_args = []
        minibox_args.append(f"--time={self.time_limit}")
        minibox_args.append(f"--wall-time={self.clock_limit}")
        minibox_args.append(f"--mem={self.mem_limit*1024}")
        minibox_args.append(f"--processes={self.process_limit}")

        for std in ("stdin", "stdout", "stderr"):
            attr = getattr(self, std)
            if isinstance(attr, TaskPath):
                minibox_args.append(f"--{std}={attr.path}")
            elif getattr(self, std) is None and std != "stderr":
                minibox_args.append(f"--{std}=/dev/null")

            if isinstance(attr, int):
                result[std] = attr
            else:
                result[std] = subprocess.PIPE

        for key, val in self.env.items():
            minibox_args.append(f"--env={key}={val}")

        minibox_args.append(f"--silent")
        minibox_args.append(f"--meta={meta_file}")

        result["args"] = (
            [minibox] + minibox_args + ["--run", "--", self.executable.path] + self.args
        )
        return result


class ProgramsJob(TaskJob):
    """Job that deals with a program."""

    def __init__(self, env: Env, name: str, **kwargs) -> None:
        super().__init__(env=env, name=name, **kwargs)
        self._program_pool: list[ProgramPoolItem] = []
        self._callback: Optional[Callable[[subprocess.Popen], None]] = None

    def _load_compiled(self, program: TaskPath) -> TaskPath:
        """Loads name of compiled program."""
        executable = TaskPath.executable_file(self._env, program.path)
        if not self._file_exists(executable):
            raise PipelineItemFailure(
                f"Program {executable:p} does not exist, "
                f"although it should have been compiled already."
            )
        return executable

    def _load_program(
        self,
        program_type: ProgramType,
        program: TaskPath,
        args: list[str] = [],
        stdin: Optional[Union[TaskPath, int]] = None,
        stdout: Optional[Union[TaskPath, int]] = None,
        stderr: Optional[TaskPath] = None,
        env={},
    ) -> None:
        """Adds program to execution pool."""
        executable = self._load_compiled(program)

        self._access_file(executable)
        if isinstance(stdin, TaskPath):
            self._access_file(stdin)
        if isinstance(stdout, TaskPath):
            self.make_filedirs(stdout)
            self._access_file(stdout)
        if isinstance(stderr, TaskPath):
            self.make_filedirs(stderr)
            self._access_file(stderr)

        self._program_pool.append(
            ProgramPoolItem(
                executable=executable,
                args=args,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                env=env,
                **self._get_limits(program_type),
            )
        )

    def _load_callback(self, callback: Callable[[subprocess.Popen], None]) -> None:
        if self._callback is not None:
            raise RuntimeError("Callback already loaded.")
        self._callback = callback

    def _run_programs(self, print_first_stderr=False) -> list[RunResult]:
        """Runs all programs in execution pool."""
        running_pool: list[subprocess.Popen] = []
        meta_files: list[str] = []
        minibox = TaskPath.executable_path(self._env, "minibox").path
        for pool_item in self._program_pool:
            fd, meta_file = tempfile.mkstemp()
            os.close(fd)
            meta_files.append(meta_file)

            running_pool.append(
                subprocess.Popen(**pool_item.to_popen(minibox, meta_file))
            )

        stderr_raw = ""
        callback_exec = False
        while True:
            states = [process.poll() is not None for process in running_pool]
            if not callback_exec and any(states):
                callback_exec = True
                if self._callback is not None:
                    self._callback(running_pool[states.index(True)])

            if print_first_stderr:
                assert running_pool[0].stderr is not None  # To make mypy happy
                line = running_pool[0].stderr.read().decode()
                if line:
                    stderr_raw += line
                    self._print(
                        colored_env(line, "yellow", self._env), end="", stderr=True
                    )

            if all(states):
                break

        run_results = []
        for pool_item, (process, meta_file) in zip(
            self._program_pool, zip(running_pool, meta_files)
        ):
            process.wait()
            assert process.stderr is not None  # To make mypy happy

            with open(meta_file) as f:
                meta_raw = f.read().strip().split("\n")

            assert meta_file.startswith("/tmp")  # Better safe then sorry
            os.remove(meta_file)

            meta = {key: val for key, val in map(lambda x: x.split(":", 1), meta_raw)}
            if not print_first_stderr:
                stderr_raw = process.stderr.read().decode()
            stderr_text = None if pool_item.stderr else stderr_raw
            if process.returncode == 0:
                t, wt = float(meta["time"]), float(meta["time-wall"])
                run_results.append(
                    RunResult(
                        RunResultKind.OK,
                        0,
                        t,
                        wt,
                        pool_item.stdout,
                        pool_item.stderr,
                        stderr_text,
                        "Finished successfully",
                    )
                )
            elif process.returncode == 1:
                t, wt = float(meta["time"]), float(meta["time-wall"])
                if meta["status"] in ("RE", "SG"):
                    if meta["status"] == "RE":
                        return_code = int(meta["exitcode"])
                    elif meta["status"] == "SG":
                        return_code = int(meta["exitsig"])
                        meta["message"] += f" ({signal.Signals(return_code).name})"

                    run_results.append(
                        RunResult(
                            RunResultKind.RUNTIME_ERROR,
                            return_code,
                            t,
                            wt,
                            pool_item.stdout,
                            pool_item.stderr,
                            stderr_text,
                            meta["message"],
                        )
                    )
                elif meta["status"] == "TO":
                    run_results.append(
                        RunResult(
                            RunResultKind.TIMEOUT,
                            -1,
                            t,
                            wt,
                            pool_item.stdout,
                            pool_item.stderr,
                            stderr_text,
                            f"Timeout after {pool_item.time_limit}s",
                        )
                    )
                else:
                    raise RuntimeError(f"Unknown minibox status {meta['message']}.")
            else:
                raise PipelineItemFailure(f"Minibox error:\n{tab(stderr_raw)}")

        return run_results

    def _run_program(
        self,
        program_type: ProgramType,
        program: TaskPath,
        print_first_stderr=False,
        **kwargs,
    ) -> RunResult:
        """Loads one program and runs it."""
        self._load_program(program_type, program, **kwargs)
        return self._run_programs(print_first_stderr)[0]

    def _create_program_failure(self, msg: str, res: RunResult):
        """Create PipelineItemFailure that nicely formats RunResult"""
        return PipelineItemFailure(f"{msg}\n{tab(self._quote_program(res))}")

    def _quote_program(self, res: RunResult):
        """Quotes program's stdout and stderr."""
        program_msg = f"status: {res.status}\n"
        for std in ("stdout", "stderr"):
            program_msg += f"{std}{getattr(res, std)(self._env, self._access_file)}\n"
        return program_msg[:-1]
