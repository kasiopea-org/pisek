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

import configparser
import os
import re
from typing import Union, Optional, TypeVar, Callable

from pisek.terminal import tab, eprint

DEFAULT_TIMEOUT: float = 360.0
CONFIG_FILENAME = "config"
DATA_SUBDIR = "data/"

from pisek.env import BaseEnv


class TaskConfigError(Exception):
    pass


class TaskConfigMissingSection(TaskConfigError):
    def __init__(self, section: str, *args: object) -> None:
        super().__init__(f"Missing section [{section}]", *args)


class TaskConfigMissingOption(TaskConfigError):
    def __init__(self, section: str, option: str, *args: object) -> None:
        super().__init__(f"Missing option '{option}' in section [{section}]", *args)


class TaskConfigWrongValue(TaskConfigError):
    def __init__(
        self, section: str, option: str, value: str, type_: type, *args: object
    ) -> None:
        super().__init__(
            f"Invalid value for option '{option}' in section [{section}]: '{value}' should be {type_}",
            *args,
        )


class TaskConfigParser(configparser.RawConfigParser):
    """
    https://stackoverflow.com/questions/573WrongOpconfigparser-get-list-of-unused-entries
    Modified ConfigParser:
        - allows checking whether there are unused keys.
        - raises custom errors
    """

    used_vars: dict[str, set] = {}

    def get_unused_keys(self, section):
        all_options = self.options(section)

        # We need the default in case the section is not present at all.
        section_used_vars = self.used_vars.get(section, [])

        unused_options = [x for x in all_options if x not in section_used_vars]
        return unused_options

    def get(
        self,
        section,
        option,
        *,
        type_=str,
        raw=False,
        vars=None,
        fallback=configparser._UNSET,
    ):
        if section not in self:
            if fallback == configparser._UNSET:
                raise TaskConfigMissingSection(section)
            else:
                return fallback
        if option not in self[section]:
            if fallback == configparser._UNSET:
                raise TaskConfigMissingOption(section, option)
            else:
                return fallback

        if section not in self.used_vars:
            self.used_vars[section] = [option]
        else:
            self.used_vars[section].append(option)

        val = super().get(section, option, raw=raw, vars=vars, fallback=fallback)
        try:
            return type_(val)
        except ValueError:
            raise TaskConfigWrongValue(section, option, val, type_)


class TaskConfig(BaseEnv):
    def __init__(self, task_dir: str):
        super().__init__()

        config = TaskConfigParser()
        self["_config_path"] = os.path.join(task_dir, CONFIG_FILENAME)
        read_files = config.read(self._config_path)
        if not read_files:
            raise TaskConfigError(
                f"No configuration file {self._config_path}. Is this task folder?"
            )

        self["task_dir"] = task_dir

        if (raw_version := config.get("task", "version", fallback=None)) == None:
            raise TaskConfigError(
                f"Config is of former version. Upgrade it with `pisek update`"
            )
        if raw_version[0] != "v":
            raise TaskConfigError(
                f"Invalid version: {raw_version} (version must begin with v)"
            )
        try:
            version = int(raw_version[1:])
        except ValueError:
            raise TaskConfigError(f"Invalid version: {raw_version}")
        if version < 2:
            raise TaskConfigError(
                f"Config is of former version. Upgrade it with `pisek update`"
            )
        elif version > 2:
            raise TaskConfigError(f"Unknown config version: {raw_version}")

        self["task_name"] = config.get("task", "name")

        self["contest_type"] = config.get("task", "contest_type", fallback="kasiopea")
        self["task_type"] = config.get("task", "task_type", fallback="batch")

        self["generator"] = config.get("tests", "in_gen")
        self["checker"] = config.get("tests", "checker", fallback=None)
        self["judge_type"] = config.get("tests", "out_check", fallback="diff")
        if self.task_type == "communication" and self.judge_type != "judge":
            raise TaskConfigError(f"For communication task 'out_check' must be 'judge'.")

        if self.judge_type == "judge":
            self["judge"] = config.get("tests", "out_judge")
            self["judge_needs_in"] = config.get(
                "tests", "judge_needs_in", type_=int, fallback=1
            )
            self["judge_needs_out"] = config.get(
                "tests", "judge_needs_out", type_=int, fallback=1
            )
        else:
            self["judge"] = "diff"
            self["judge_needs_in"] = 0
            self["judge_needs_out"] = 1

        self["fail_mode"] = "all" if self.contest_type == "kasiopea" else "any"
        # Relevant for CMS interactive tasks. The file to be linked with
        # the contestant's solution (primarily for C++)
        self["solution_manager"] = config.get(
            "tests", "solution_manager", fallback=None
        )

        self["timeout_model_solution"] = config.get(
            "limits", "solve_time_limit", type_=float, fallback=DEFAULT_TIMEOUT
        )
        self["timeout_other_solutions"] = config.get(
            "limits",
            "sec_solve_time_limit",
            type_=float,
            fallback=self.timeout_model_solution,
        )

        if self.contest_type == "kasiopea":
            self["input_max_size"] = config.get(
                "limits", "input_max_size", type_=int, fallback=50
            )  # MB
            self["output_max_size"] = config.get(
                "limits", "output_max_size", type_=int, fallback=10
            )  # MB

        # Support for different directory structures
        self["static_subdir"] = config.get("task", "static_subdir", fallback=".")
        self["data_subdir"] = config.get("task", "data_subdir", fallback=DATA_SUBDIR)
        self["solutions_subdir"] = config.get("task", "solutions_subdir", fallback=".")

        subtasks: dict[str, SubtaskConfig] = {}
        self["_subtask_section_names"] = set()

        for section_name in config.sections():
            m = re.match(r"test([0-9]{2})", section_name)

            if not m:
                # One of the other sections ([task], [tests]...)
                continue

            self._subtask_section_names.add(section_name)

            subtask_number = int(m.groups()[0])
            if subtask_number in subtasks:
                raise TaskConfigError(f"Duplicate subtask number {subtask_number}")

            try:
                subtasks[str(subtask_number)] = SubtaskConfig(
                    subtask_number, config[section_name]
                )
            except TaskConfigError as err:
                raise TaskConfigError(
                    f"Error while loading subtask {m[0]}:\n{tab(str(err))}"
                )

        if "0" not in subtasks:  # Add samples
            subtasks["0"] = SubtaskConfig(
                0, configparser.SectionProxy(config, "test00")
            )

        total_points = sum(map(lambda s: s.score, subtasks.values()))

        # subtask should be ordered by number
        subtasks = {key: val for key, val in sorted(subtasks.items())}

        all_globs: set[str] = set([])
        for subtask in subtasks.values():
            subtask.construct_globs(subtasks)
            all_globs = all_globs.union(subtask.in_globs)

        self["subtasks"] = BaseEnv(**subtasks, all_globs=list(sorted(all_globs)))

        self["_solution_section_names"] = set()
        solutions = {}
        primary = None
        for section_name in config.sections():
            m = re.match(r"solution_(.*)", section_name)

            if not m:
                # One of the other sections ([task], [tests]...)
                continue
            self._solution_section_names.add(m[0])
            solution = m[1]

            try:
                solutions[solution] = SolutionConfig(
                    solution, total_points, len(subtasks), config[section_name]
                )
            except TaskConfigError as err:
                raise TaskConfigError(
                    f"Error while loading solution {solution}:\n{tab(str(err))}"
                )

            if solutions[solution].primary:
                if primary is None:
                    primary = solution
                else:
                    raise TaskConfigError(
                        f"Multiple primary solutions: {primary} and {solution}"
                    )

        if len(solutions) and primary is None:
            raise TaskConfigError("No primary solution set.")

        self["solutions"] = BaseEnv(**solutions)
        self["primary_solution"] = primary

        self.check_unused_keys(config)

    def get_maximum_score(self) -> int:
        return sum([subtask.score for _, subtask in self.subtasks.subenvs()])

    def get_data_dir(self):
        return os.path.normpath(os.path.join(self.task_dir, self.data_subdir))

    def get_static_dir(self):
        return os.path.normpath(os.path.join(self.task_dir, self.static_subdir))

    def get_timeout(self, is_secondary_solution: bool) -> float:
        return (
            (self.timeout_other_solutions if is_secondary_solution else None)
            or self.timeout_model_solution
            or DEFAULT_TIMEOUT
        )

    def check_todos(self) -> bool:
        """Check whether config contains TODO in comments."""
        with open(self._config_path) as config:
            for line in config:
                if "#" in line and "TODO" in line.split("#")[1]:
                    return True

        return False

    @BaseEnv.log_off
    def check_unused_keys(self, config: TaskConfigParser) -> None:
        """Verify that there are no unused keys in the config, raise otherwise."""

        accepted_section_names = (
            self._subtask_section_names
            | self._solution_section_names
            | {
                "task",
                "tests",
                "limits",
            }
        )

        # These keys are accepted for backwards compatibility reasons because the config
        # format is based on KSP's opendata tool.
        ignored_keys = {
            "task": {"tests"},
            "tests": {"in_mode", "out_mode", "out_format", "online_validity"},
            "limits": {},
            # Any subtask section like "test01", "test02"...
            "subtask": {"file_name"},
            # Any solution section like solution_solve, solution_slow, ...
            "solution": {},
        }

        for section_name in config.sections():
            if not section_name in accepted_section_names:
                raise TaskConfigError(f"Unexpected section [{section_name}] in config")

            if section_name in self._subtask_section_names:
                section_ignored_keys = ignored_keys["subtask"]
            elif section_name in self._solution_section_names:
                section_ignored_keys = ignored_keys["solution"]
            else:
                section_ignored_keys = ignored_keys[section_name]

            for key in config.get_unused_keys(section_name):
                if key not in section_ignored_keys:
                    raise TaskConfigError(
                        f"Unexpected key '{key}' in section [{section_name}] of config."
                    )

        return None


class SubtaskConfig(BaseEnv):
    def __init__(self, subtask_number: int, config_section: configparser.SectionProxy):
        super().__init__()

        if subtask_number == 0:  # samples
            self["name"] = config_section.get("name", "Samples")
            self["score"] = int(
                config_section.get("points", type_=int, fallback="0")
            )  # To make mypy happy
            self["in_globs"] = tuple(
                config_section.get("in_globs", "sample*.in").split()
            )
            self["predecessors"] = config_section.get("predecessors", "").split()
        else:
            self["name"] = config_section.get("name", None)
            self["score"] = config_section.get("points", type_=int)
            if self.score is None:
                raise TaskConfigMissingOption(config_section.name, "points")
            self["in_globs"] = tuple(
                config_section.get("in_globs", self._glob_i(subtask_number)).split()
            )
            if not all(glob.endswith(".in") for glob in self.in_globs):
                raise TaskConfigError(
                    f"All in_globs must end with '.in': {' '.join(self.in_globs)}"
                )
            prev = "" if subtask_number == 1 else str(subtask_number - 1)
            self["predecessors"] = config_section.get("predecessors", prev).split()
        self["_constructing"] = False

    def _glob_i(self, i: int):
        return f"{i:02}*.in"

    @BaseEnv.log_off
    def construct_globs(self, subtasks) -> list[str]:
        if self._constructing:
            raise TaskConfigError("Cyclic predecessors subtasks.")
        self["_constructing"] = True
        if "all_globs" not in self._vars:
            all_globs = set(self.in_globs)
            for prev in self.predecessors:
                if str(prev) not in subtasks:
                    raise TaskConfigError(f"No predecessor subtask with number {prev}")
                prev_globs = subtasks[str(prev)].construct_globs(subtasks)
                for glob in prev_globs:
                    all_globs.add(glob)
            self["all_globs"] = tuple(sorted(all_globs))

        self["_constructing"] = False
        return self.all_globs


class SolutionConfig(BaseEnv):
    def __init__(
        self,
        solution_name: str,
        full_points: int,
        total_subtasks: int,
        config_section: configparser.SectionProxy,
    ) -> None:
        super().__init__()

        if "." in solution_name:
            raise TaskConfigError(
                f"Character '.' is not allowed in section name: {solution_name}"
            )
        self["source"] = config_section.get("source", solution_name)
        primary = config_section.get("primary", "no").lower()
        if primary not in ("yes", "no"):
            raise TaskConfigError(
                f"Key 'primary' should be one of (yes, no): {primary}"
            )
        self["primary"] = primary == "yes"

        points = config_section.get("points")

        for points_limit in ["points_above", "points_below"]:
            if points is not None and points_limit in config_section:
                raise TaskConfigError(
                    f"Both 'points' and '{points_limit}' are present in section [{solution_name}]."
                )

        points_above = config_section.get("points_above", points)
        points_below = config_section.get("points_below", points)

        for name, value in [
            ("points", points),
            ("points_above", points_above),
            ("points_below", points_below),
        ]:
            if value is None or value == "X":
                self[name] = None
            else:
                try:
                    value = float(value)
                except ValueError:
                    raise TaskConfigError(
                        f"{name} must be one of ('X', int) but is: {value}"
                    )
                self[name] = value

        subtasks = config_section.get("subtasks")
        if subtasks is None:
            subtasks = [1 if self.primary else None] * total_subtasks
        else:
            subtasks_str = subtasks.strip()
            if len(subtasks_str) != total_subtasks:
                raise TaskConfigError(
                    f"There are {total_subtasks} but subtasks string has {len(subtasks_str)} characters: '{subtasks_str}'"
                )
            subtasks = []
            for char in subtasks_str:
                if char == "1":
                    subtasks.append(1)
                elif char == "0":
                    subtasks.append(0)
                elif char == "X":
                    subtasks.append(None)
                else:
                    raise TaskConfigError(f"Unallowed char in subtask string: {char}")

        if self.primary and not all(map(lambda p: p == 1, subtasks)):
            raise TaskConfigError(
                f"Primary solution '{solution_name}' must have: subtasks={'1'*total_subtasks}"
            )

        self["subtasks"] = subtasks


def load_config(path: str) -> Optional[TaskConfig]:
    try:
        return TaskConfig(path)
    except TaskConfigError as err:
        eprint(f"Error while loading config:\n{tab(str(err))}")
        return None
