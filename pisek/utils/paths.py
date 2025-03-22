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

from dataclasses import dataclass
import os
from typing import Optional, TYPE_CHECKING
from pisek.config.config_types import DataFormat

if TYPE_CHECKING:
    from pisek.env.env import Env

BUILD_DIR = "build/"
TESTS_DIR = "tests/"
INTERNALS_DIR = ".pisek/"

GENERATED_SUBDIR = "_generated/"
INPUTS_SUBDIR = "_inputs/"
FUZZING_OUTPUTS_SUBDIR = "_fuzzing/"


@dataclass(frozen=True)
class TaskPath:
    """Class representing a path to task file."""

    path: str

    def __init__(self, *path: str):
        joined_path = os.path.normpath(os.path.join(*path))
        object.__setattr__(self, "path", joined_path)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(path={self.path})"

    def __init_subclass__(cls):
        return super().__init_subclass__()

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    def __format__(self, __format_spec: str) -> str:
        match __format_spec:
            case "":
                return self.path
            case "p":
                return self.path
            case "n":
                return self.name
            case _:
                raise ValueError(
                    f"Invalid format specifier '{__format_spec}' for object of type '{self.__class__.__name__}'"
                )

    def __eq__(self, other_path) -> bool:
        if isinstance(other_path, TaskPath):
            return self.path == other_path.path
        else:
            return False

    def __lt__(self, other_path: "TaskPath") -> bool:
        return self.path < other_path.path

    def col(self, env: "Env") -> str:
        return env.colored(
            self.path + ("/" if os.path.isdir(self.path) else ""), "magenta"
        )

    def replace_suffix(self, new_suffix: str) -> "TaskPath":
        path = os.path.splitext(self.path)[0] + new_suffix
        return TaskPath(path)

    def join(self, *path: str) -> "TaskPath":
        return TaskPath(os.path.join(self.path, *path))

    def exists(self) -> bool:
        return os.path.exists(self.path)

    @staticmethod
    def from_abspath(*path: str) -> "TaskPath":
        return TaskPath(os.path.relpath(os.path.join(*path), "."))

    @staticmethod
    def static_path(env: "Env", *path: str) -> "TaskPath":
        return env.config.static_subdir.join(*path)

    @staticmethod
    def executable_path(env: "Env", *path: str) -> "TaskPath":
        return TaskPath(BUILD_DIR, *path)

    @staticmethod
    def executable_file(env: "Env", program: str) -> "TaskPath":
        program = os.path.splitext(program)[0]
        return TaskPath.executable_path(env, program)

    @staticmethod
    def data_path(env: "Env", *path: str) -> "TaskPath":
        return TaskPath(TESTS_DIR, *path)

    @staticmethod
    def generated_path(env: "Env", *path: str) -> "TaskPath":
        return TaskPath.data_path(env, GENERATED_SUBDIR, *path)


class JudgeablePath(TaskPath):
    def to_judge_log(self, judge: str) -> "LogPath":
        return LogPath(self.replace_suffix(f".{os.path.basename(judge)}.log").path)


class SanitizablePath(TaskPath):
    def to_raw(self, format: DataFormat) -> "RawPath":
        if format == DataFormat.binary:
            return RawPath(self.path)
        return RawPath(self.path + ".raw")


class InputPath(SanitizablePath):
    def __init__(self, env: "Env", *path, solution: Optional[str] = None) -> None:
        if solution is None:
            super().__init__(TESTS_DIR, INPUTS_SUBDIR, *path)
        else:
            super().__init__(TESTS_DIR, solution, *path)

    def to_output(self) -> "OutputPath":
        return OutputPath(self.replace_suffix(f".out").path)

    def to_log(self, program: str) -> "LogPath":
        return LogPath(self.replace_suffix(f".{os.path.basename(program)}.log").path)


class OutputPath(JudgeablePath, SanitizablePath):
    @staticmethod
    def static(*path) -> "OutputPath":
        return OutputPath(TESTS_DIR, INPUTS_SUBDIR, *path)

    def to_reference_output(self) -> "OutputPath":
        return OutputPath(self.replace_suffix(f".ok").path)

    def to_fuzzing(self, seed: int) -> "OutputPath":
        return OutputPath(
            TESTS_DIR,
            FUZZING_OUTPUTS_SUBDIR,
            self.replace_suffix(f".{seed:x}.out").name,
        )


class LogPath(JudgeablePath):
    @staticmethod
    def generator_log(generator: str) -> "LogPath":
        return LogPath(TESTS_DIR, INPUTS_SUBDIR, f"{os.path.basename(generator)}.log")


class RawPath(TaskPath):
    def to_sanitized_output(self) -> OutputPath:
        return OutputPath(self.path.removesuffix(".raw"))

    def to_sanitized_input(self, env: "Env") -> InputPath:
        return InputPath(env, self.path.removesuffix(".raw"))

    def to_second(self) -> TaskPath:
        return self.replace_suffix(".raw2")
