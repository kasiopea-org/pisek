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
import yaml

from pisek.env.env import Env

BUILD_DIR = "build/"

GENERATED_SUBDIR = "generated/"
INPUTS_SUBDIR = "inputs/"
INVALID_OUTPUTS_SUBDIR = "invalid/"
OUTPUTS_SUBDIR = "outputs/"
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

    def replace_suffix(self, new_suffix: str) -> "TaskPath":
        path = os.path.splitext(self.path)[0] + new_suffix
        return TaskPath(path)

    @staticmethod
    def from_abspath(*path: str) -> "TaskPath":
        return TaskPath(os.path.relpath(os.path.join(*path), "."))

    @staticmethod
    def static_path(env: Env, *path: str) -> "TaskPath":
        return TaskPath(env.config.static_subdir, *path)

    @staticmethod
    def solution_path(env: Env, *path: str) -> "TaskPath":
        return TaskPath(env.config.solutions_subdir, *path)

    @staticmethod
    def executable_path(env: Env, *path: str) -> "TaskPath":
        return TaskPath(BUILD_DIR, *path)

    @staticmethod
    def executable_file(env: Env, program: str) -> "TaskPath":
        program = os.path.splitext(os.path.basename(program))[0]
        return TaskPath.executable_path(env, program)

    @staticmethod
    def data_path(env: Env, *path: str) -> "TaskPath":
        return TaskPath(env.config.data_subdir, *path)

    @staticmethod
    def generated_path(env: Env, *path: str) -> "TaskPath":
        return TaskPath.data_path(env, GENERATED_SUBDIR, *path)

    @staticmethod
    def generated_input_file(env: Env, subtask: int, seed: int) -> "TaskPath":
        return TaskPath.generated_path(env, f"{subtask:02}_{seed:x}.in")

    @staticmethod
    def input_path(env: Env, *path: str) -> "TaskPath":
        return TaskPath.data_path(env, INPUTS_SUBDIR, *path)

    @staticmethod
    def invalid_path(env: Env, *path: str) -> "TaskPath":
        return TaskPath.data_path(env, INVALID_OUTPUTS_SUBDIR, *path)

    @staticmethod
    def invalid_file(env: Env, name: str, seed: int) -> "TaskPath":
        name = os.path.splitext(name)[0]
        return TaskPath.invalid_path(env, f"{name}.{seed:x}.invalid")

    @staticmethod
    def output_path(env: Env, *path: str) -> "TaskPath":
        return TaskPath.data_path(env, OUTPUTS_SUBDIR, *path)

    @staticmethod
    def output_file(env: Env, input_name: str, solution: str) -> "TaskPath":
        input_name = os.path.splitext(os.path.basename(input_name))[0]
        solution = os.path.basename(solution)
        return TaskPath.output_path(env, f"{input_name}.{solution}.out")

    @staticmethod
    def output_static_file(env: Env, name: str) -> "TaskPath":
        name = os.path.splitext(name)[0]
        return TaskPath.output_path(env, f"{name}.out")

    @staticmethod
    def sanitized_path(env: Env, *path: str) -> "TaskPath":
        return TaskPath.data_path(env, SANITIZED_SUBDIR, *path)

    @staticmethod
    def sanitized_file(env: Env, name: str) -> "TaskPath":
        name = os.path.basename(name)
        return TaskPath.sanitized_path(env, f"{name}.clean")

    @staticmethod
    def log_path(env: Env, *path: str) -> "TaskPath":
        return TaskPath.data_path(env, LOG_SUBDIR, *path)

    @staticmethod
    def points_file(env: Env, name: str) -> "TaskPath":
        name = os.path.splitext(name)[0]
        return TaskPath.log_path(env, f"{name}.points")

    @staticmethod
    def log_file(env: Env, name: str, program: str) -> "TaskPath":
        name = os.path.splitext(os.path.basename(name))[0]
        program = os.path.basename(program)
        return TaskPath.log_path(env, f"{name}.{program}.log")


def task_path_representer(dumper, task_path: TaskPath):
    return dumper.represent_sequence("!TaskPath", [task_path.path])


def task_path_constructor(loader, value):
    [path] = loader.construct_sequence(value)
    return TaskPath(path)


yaml.add_representer(TaskPath, task_path_representer)
yaml.add_constructor("!TaskPath", task_path_constructor)
