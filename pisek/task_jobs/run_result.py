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
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

from pisek.utils.paths import TaskPath


class RunResultKind(Enum):
    OK = 0
    RUNTIME_ERROR = 1
    TIMEOUT = 2


@dataclass(frozen=True)
class RunResult:
    """Represents the way the program execution ended. Specially, a program
    that finished successfully, but got Wrong Answer, still gets the OK
    RunResult."""

    kind: RunResultKind
    returncode: int
    time: float
    wall_time: float
    stdout_file: Optional[Union[TaskPath, int]] = None
    stderr_file: Optional[TaskPath] = None
    status: str = ""
