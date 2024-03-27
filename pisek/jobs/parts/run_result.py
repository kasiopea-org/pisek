# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from enum import Enum
from typing import Optional, Union
import yaml

from pisek.utils.paths import TaskPath


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
        status: str = "",
    ):
        self.kind = kind
        self.returncode = returncode
        self.stdout_file = stdout_file
        self.stderr_file = stderr_file
        self.status = status
        self.time = time
        self.wall_time = wall_time


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
        status,
    ) = loader.construct_sequence(value)
    return RunResult(
        RunResultKind[kind], returncode, time, wall_time, out_f, err_f, status
    )


yaml.add_representer(RunResult, run_result_representer)
yaml.add_constructor("!RunResult", run_result_constructor)
