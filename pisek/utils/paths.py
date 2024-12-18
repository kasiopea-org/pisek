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
import yaml

if TYPE_CHECKING:
    from pisek.env.env import Env

BUILD_DIR = "build/"
TESTS_DIR = "tests/"

GENERATED_SUBDIR = "generated/"
INPUTS_SUBDIR = "inputs/"
INVALID_OUTPUTS_SUBDIR = "invalid/"
SANITIZED_SUBDIR = "sanitized/"
LOG_SUBDIR = "log/"


@dataclass(frozen=True)
class TaskPath:
    """Class representing a path to task file."""

    path: str
    name: str

    def __init__(self, *path: str):
        joined_path = os.path.normpath(os.path.join(*path))
        object.__setattr__(self, "path", joined_path)
        object.__setattr__(self, "name", os.path.basename(joined_path))

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

    def col(self, env: "Env") -> str:
        return env.colored(self.path, "magenta")

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
    def solution_path(env: "Env", *path: str) -> "TaskPath":
        return env.config.solutions_subdir.join(*path)

    @staticmethod
    def executable_path(env: "Env", *path: str) -> "TaskPath":
        return TaskPath(BUILD_DIR, *path)

    @staticmethod
    def executable_file(env: "Env", program: str) -> "TaskPath":
        program = os.path.splitext(os.path.basename(program))[0]
        return TaskPath.executable_path(env, program)

    @staticmethod
    def data_path(env: "Env", *path: str) -> "TaskPath":
        return TaskPath(TESTS_DIR, *path)

    @staticmethod
    def generated_path(env: "Env", *path: str) -> "TaskPath":
        return TaskPath.data_path(env, GENERATED_SUBDIR, *path)


class JudgeablePath(TaskPath):
    def to_judge_log(self, judge: str) -> "LogPath":
        return LogPath(os.path.splitext(self.path)[0] + f".{judge}.log")


class SanitizeablePath(TaskPath):
    def to_sanitized(self) -> "SanitizedPath":
        return SanitizedPath(TESTS_DIR, SANITIZED_SUBDIR, self.name + ".clean")


class InputPath(SanitizeablePath):
    def __init__(self, env: "Env", *path, solution: Optional[str] = None) -> None:
        if solution is None:
            super().__init__(TESTS_DIR, INPUTS_SUBDIR, *path)
        else:
            super().__init__(
                TESTS_DIR, env.config.solutions[solution].raw_source, *path
            )

    def to_output(self, solution: str) -> "OutputPath":
        return OutputPath(os.path.splitext(self.path)[0] + f".{solution}.out")

    def to_log(self, program: str) -> "LogPath":
        return LogPath(os.path.splitext(self.path)[0] + f".{program}.log")


class OutputPath(JudgeablePath, SanitizeablePath):
    @staticmethod
    def static(*path) -> "OutputPath":
        return OutputPath(TESTS_DIR, INPUTS_SUBDIR, *path)

    def to_invalid(self, seed: int) -> "OutputPath":
        return OutputPath(
            TESTS_DIR,
            INVALID_OUTPUTS_SUBDIR,
            os.path.splitext(self.name)[0] + f".{seed:x}.invalid",
        )


class LogPath(JudgeablePath):
    @staticmethod
    def generator_log(generator: str) -> "LogPath":
        return LogPath(TESTS_DIR, INPUTS_SUBDIR, f"{generator}.log")


class SanitizedPath(TaskPath):
    pass


def task_path_representer(dumper, task_path: TaskPath):
    return dumper.represent_sequence("!TaskPath", [task_path.path])


def task_path_constructor(loader, value):
    [path] = loader.construct_sequence(value)
    return TaskPath(path)


yaml.add_representer(TaskPath, task_path_representer)
yaml.add_constructor("!TaskPath", task_path_constructor)
