# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>

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

DEFAULT_TIMEOUT : float = 360
CONFIG_FILENAME = "config"
DATA_SUBDIR = "data/"

from pisek.env import BaseEnv

class CheckedConfigParser(configparser.RawConfigParser):
    """
    https://stackoverflow.com/questions/57305229/python-configparser-get-list-of-unused-entries
    Like ConfigParser, but allows checking whether there are unused keys.
    """

    used_vars: dict[str, set] = {}

    def get_unused_keys(self, section):
        all_options = self.options(section)

        # We need the default in case the section is not present at all.
        section_used_vars = self.used_vars.get(section, [])

        unused_options = [x for x in all_options if x not in section_used_vars]
        return unused_options

    def get(
        self, section, option, *, raw=False, vars=None, fallback=configparser._UNSET
    ):
        if section not in self.used_vars:
            self.used_vars[section] = [option]
        else:
            self.used_vars[section].append(option)
        return super().get(section, option, raw=raw, vars=vars, fallback=fallback)

    def _get(self, section, conv, option, **kwargs):
        if section not in self.used_vars:
            self.used_vars[section] = [option]
        else:
            self.used_vars[section].append(option)
        return super()._get(section, conv, option, **kwargs)


class TaskConfig(BaseEnv):
    def __init__(self, task_dir: str) -> None:
        super().__init__()
        self._task_dir = task_dir

    def load(self) -> Optional[str]:
        config = CheckedConfigParser()
        config_path = os.path.join(self._task_dir, CONFIG_FILENAME)
        read_files = config.read(config_path)
        if not read_files:
            return f"No configuration file {config_path}. Is this task folder?"
        
        self._set("task_dir", self._task_dir)

        needed_sections = ["task", "tests"]
        for section in needed_sections:
            if section not in config:
                return f"Missing section [{section}]"
        
        needed_keys = [("task", "solutions"), ("tests", "in_gen")]
        if config["tests"].get("out_check") == "judge":
            needed_keys.append(("tests", "out_judge"))
        for section, key in needed_keys:
            if config.get(section, key) is None:
                return f"Missing key '{key}' in section [{section}]"

        self._set("task_name", config.get("task", "name"))

        solutions = config.get("task", "solutions").split()
        if len(solutions) == 0:
            return "No solutions in config"
        self._set("solutions", solutions)
        self._set("primary_solution", solutions[0])

        self._set("contest_type", contest_type := config["task"].get("contest_type", "kasiopea"))

        self._set("generator", config["tests"]["in_gen"])
        self._set("checker", config["tests"].get("checker"))
        self._set("judge_type", judge_type := config["tests"].get("out_check", "diff"))
        if judge_type == "judge":
            self._set("judge", config["tests"]["out_judge"])
        else:
            self._set("judge", "diff")

        self._set("fail_mode", "all" if contest_type == "kasiopea" else "any")
        # Relevant for CMS interactive tasks. The file to be linked with
        # the contestant's solution (primarily for C++)
        self._set("solution_manager", config["tests"].get("solution_manager"))

        self._set("timeout_model_solution", apply_to_optional(
                config.get("limits", "solve_time_limit", fallback=None), float
            ))
        self._set("timeout_other_solutions", apply_to_optional(
            config.get("limits", "sec_solve_time_limit", fallback=None), float
        ))

        # Support for different directory structures
        self._set("samples_subdir", config["task"].get("samples_subdir", "."))
        self._set("data_subdir", config["task"].get("data_subdir", DATA_SUBDIR))
        self._set("solutions_subdir", config["task"].get("solutions_subdir", "."))

        subtasks: Dict[int, SubtaskConfig] = {}
        subtask_section_names = set()

        for section_name in config.sections():
            m = re.match(r"test([0-9]{2})", section_name)

            if not m:
                # One of the other sections ([task], [tests]...)
                continue

            subtask_section_names.add(section_name)

            subtask_number = int(m.groups()[0])
            if subtask_number in subtasks:
                return f"Duplicate subtask number {subtask_number}"

            if subtask_number > 0 and "points" not in config[section_name]:
                return f"Missing key 'points' in section [{section_name}]"

            subtasks[str(subtask_number)] = SubtaskConfig(
                subtask_number, config[section_name]
            )

        if "0" not in subtasks:  # Add samples
            subtasks["0"] = SubtaskConfig(0, configparser.SectionProxy(config, "test00"))

        self._set("subtasks", BaseEnv(**subtasks))
        self._set("subtask_section_names", subtask_section_names)

        for subtask in subtasks.values():
            err = subtask.construct_globs(subtasks)
            if isinstance(err, str):
                return err

        return self.check_unused_keys(config)

    def get_maximum_score(self) -> int:
        return sum([subtask.score for _, subtask in self.subtasks.items()])

    def get_data_dir(self):
        return os.path.normpath(os.path.join(self.task_dir, self.data_subdir))

    def get_samples_dir(self):
        return os.path.normpath(os.path.join(self.task_dir, self.samples_subdir))

    def get_timeout(self, is_secondary_solution : bool) -> float:
        return (self.timeout_other_solutions if is_secondary_solution else None) or \
               self.timeout_model_solution or \
               DEFAULT_TIMEOUT

    @BaseEnv.log_off
    def __repr__(self):
        return "<TaskConfig %s>" % ", ".join(
            f"{k} = {getattr(self, k)}"
            for k in filter(
                lambda k: not k.startswith("_") and not callable(getattr(self, k)),
                dir(self),
            )
        )

    @BaseEnv.log_off
    def check_unused_keys(self, config: CheckedConfigParser) -> Optional[str]:
        """Verify that there are no unused keys in the config, raise otherwise."""

        accepted_section_names = self.subtask_section_names | {
            "task",
            "tests",
            "limits",
        }

        # These keys are accepted for backwards compatibility reasons because the config
        # format is based on KSP's opendata tool.
        ignored_keys = {
            "task": {"tests"},
            "tests": {"in_mode", "out_mode", "out_format", "online_validity"},
            "limits": {},
            # Any subtask section like "test01", "test02"...
            "subtask": {"file_name"},
        }

        for section_name in config.sections():
            if not section_name in accepted_section_names:
                return f"Unexpected section [{section_name}] in config"

            if section_name in self.subtask_section_names:
                section_ignored_keys = ignored_keys["subtask"]
            else:
                section_ignored_keys = ignored_keys[section_name]

            for key in config.get_unused_keys(section_name):
                if key not in section_ignored_keys:
                    return f"Unexpected key '{key}' in section [{section_name}] of config."


class SubtaskConfig(BaseEnv):
    def __init__(
        self, subtask_number: int, config_section: configparser.SectionProxy
    ) -> None:
        super().__init__()
        if subtask_number == 0:  # samples
            self._set("name", config_section.get("name", "Samples"))
            self._set("score", int(config_section.get("points", 0)))
            self._set("in_globs", config_section.get("in_globs", "sample*.in").split())
            self._set("predecessors", config_section.get("predecessors", "").split())
        else:
            self._set("name", config_section.get("name", None))
            self._set("score", int(config_section["points"]))
            self._set("in_globs", config_section.get("in_globs", self._glob_i(subtask_number)).split())
            prev = "" if subtask_number == 1 else str(subtask_number-1)
            self._set("predecessors",config_section.get("predecessors", prev).split())
        self._constructing = False

    def _glob_i(self, i):
        return f"{'0'*(2 - len(str(i)))}{i}*.in"

    def _glob_to_regex(self, glob):
        """Does not return an 'anchored' regex, i.e., a* -> a.*, not ^a.*$"""
        pattern = glob.replace(".in", "").replace(".", "\\.").replace("*", ".*")
        pattern = pattern[:-2] if pattern.endswith(".*") else pattern + "$"
        if not pattern:
            pattern = ".*" # probably ok either way, but just to be sure
        return pattern
    
    def globs_regex(self) -> str:
        return "^(" + "|".join(self._glob_to_regex(glob) for glob in self.in_globs) + ")"
    
    @BaseEnv.log_off
    def construct_globs(self, subtasks) -> Union[str,list[str]]:
        if self._constructing:
            return "Cyclic predecessors subtasks."
        self._constructing = True
        if "all_globs" not in self._vars:
            all_globs = set(self.in_globs)
            for prev in self.predecessors:
                if str(prev) not in subtasks:
                    return f"No predecessor subtask with number {prev}"
                prev_globs = subtasks[str(prev)].construct_globs(subtasks)
                if isinstance(prev_globs, str):
                    return prev_globs
                for glob in prev_globs:
                    all_globs.add(glob)
            self._set("all_globs", list(sorted(all_globs)))

        self._constructing = False
        return self.all_globs


    @BaseEnv.log_off
    def __repr__(self):
        return "<SubTaskConfig %s>" % ", ".join(
            f"{k} = {getattr(self, k)}"
            for k in filter(
                lambda k: not k.startswith("_") and not callable(getattr(self, k)),
                dir(self),
            )
        )


T = TypeVar("T")
U = TypeVar("U")


def apply_to_optional(value: Optional[T], f: Callable[[T], U]) -> Optional[U]:
    return None if value is None else f(value)
