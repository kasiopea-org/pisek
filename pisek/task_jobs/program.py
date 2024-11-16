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
import os
import tempfile
from typing import Optional, Any, Union, Callable
import signal
import subprocess

from pisek.config.task_config import ProgramType
from pisek.env.env import Env
from pisek.utils.paths import TaskPath
from pisek.jobs.jobs import PipelineItemFailure
from pisek.utils.text import tab
from pisek.task_jobs.run_result import RunResultKind, RunResult
from pisek.task_jobs.task_job import TaskJob


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
            elif getattr(self, std) is None:
                minibox_args.append(f"--{std}=/dev/null")

            if isinstance(attr, int):
                result[std] = attr
            else:
                result[std] = subprocess.PIPE

        for key, val in self.env.items():
            minibox_args.append(f"--env={key}={val}")

        minibox_args.append("--silent")
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

    def _run_programs(self) -> list[RunResult]:
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

        callback_exec = False
        while True:
            states = [process.poll() is not None for process in running_pool]
            if not callback_exec and any(states):
                callback_exec = True
                if self._callback is not None:
                    self._callback(running_pool[states.index(True)])

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
                            meta["message"],
                        )
                    )
                elif meta["status"] == "TO":
                    timeout = (
                        f"{pool_item.time_limit}s"
                        if t > pool_item.time_limit
                        else f"{pool_item.clock_limit}ws"
                    )
                    run_results.append(
                        RunResult(
                            RunResultKind.TIMEOUT,
                            -1,
                            t,
                            wt,
                            pool_item.stdout,
                            pool_item.stderr,
                            f"Timeout after {timeout}",
                        )
                    )
                else:
                    raise RuntimeError(f"Unknown minibox status {meta['message']}.")
            else:
                raise PipelineItemFailure(
                    f"Minibox error:\n{tab(process.stderr.read().decode())}"
                )

        return run_results

    def _run_program(
        self,
        program_type: ProgramType,
        program: TaskPath,
        **kwargs,
    ) -> RunResult:
        """Loads one program and runs it."""
        self._load_program(program_type, program, **kwargs)
        return self._run_programs()[0]

    def _create_program_failure(self, msg: str, res: RunResult, **kwargs):
        """Create PipelineItemFailure that nicely formats RunResult"""
        return PipelineItemFailure(
            f"{msg}\n{tab(self._format_run_result(res, **kwargs))}"
        )

    def _format_run_result(
        self,
        res: RunResult,
        status: bool = True,
        stdout: bool = True,
        stdout_force_content: bool = False,
        stderr: bool = True,
        stderr_force_content: bool = False,
        time: bool = False,
    ):
        """Formats RunResult."""
        program_msg = ""
        if status:
            program_msg += f"status: {res.status}\n"

        if stdout and isinstance(res.stdout_file, TaskPath):
            program_msg += f"stdout: {self._quote_file_with_name(res.stdout_file, force_content=stdout_force_content)}"
        if stderr and isinstance(res.stderr_file, TaskPath):
            program_msg += f"stderr: {self._quote_file_with_name(res.stderr_file, force_content=stderr_force_content, style='ht')}"
        if time:
            program_msg += f"time: {res.time}\n"

        return program_msg.removesuffix("\n")
