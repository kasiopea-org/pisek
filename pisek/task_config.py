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
from typing import List, Dict, Optional, TypeVar, Callable

DEFAULT_TIMEOUT : float = 360
CONFIG_FILENAME = "config"
DATA_SUBDIR = "data/"

from pisek.env import BaseEnv
import pisek.util as util

class CheckedConfigParser(configparser.RawConfigParser):
    """
    https://stackoverflow.com/questions/57305229/python-configparser-get-list-of-unused-entries
    Like ConfigParser, but allows checking whether there are unused keys.
    """

    used_vars: Dict[str, set] = {}

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
        config = CheckedConfigParser()
        config_path = os.path.join(task_dir, CONFIG_FILENAME)
        read_files = config.read(config_path)
        self._set("task_dir", task_dir)

        if not read_files:
            raise FileNotFoundError(
                f"Chybí konfigurační soubor {config_path}, je toto složka s úlohou?"
            )

        try:
            self._set("task_name", config.get("task", "name"))
            solutions = config.get("task", "solutions").split()
            self._set("solutions", solutions)
            self._set("first_solution", solutions[0])
            self._set("contest_type", contest_type := config["task"].get("contest_type", "kasiopea"))
            self._set("generator", config["tests"]["in_gen"])
            self._set("checker", config["tests"].get("checker"))
            self._set("judge_type", judge_type := config["tests"].get("out_check", "diff"))
            self._set("judge", "diff")
            if judge_type == "judge":
                self._set("judge", config["tests"]["out_judge"])

            self._set("fail_mode", "all" if contest_type == "kasiopea" else "any")
            # Relevant for CMS interactive tasks. The file to be linked with
            # the contestant's solution (primarily for C++)
            solution_manager = config["tests"].get("solution_manager")
            if solution_manager:
                self._set("solution_manager", os.path.join(self.task_dir, solution_manager))

            if contest_type == "cms":
                # Warning: these timeouts are currently ignored in Kasiopea!
                self._set("timeout_model_solution", apply_to_optional(
                    config.get("limits", "solve_time_limit", fallback=None), float
                ))
                self._set("timeout_other_solutions", apply_to_optional(
                    config.get("limits", "sec_solve_time_limit", fallback=None), float
                ))

            # Support for different directory structures
            self._set("samples_subdir", config["task"].get("samples_subdir", "."))
            self._set("data_subdir", config["task"].get("data_subdir", DATA_SUBDIR))

            if "solutions_subdir" in config["task"]:
                # Prefix each solution name with solutions_subdir/
                subdir = config["task"].get("solutions_subdir", ".")
                self._set("solutions", [os.path.join(subdir, sol) for sol in self.get_without_log("solutions")])

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
                    raise ValueError("Duplicate subtask number {}".format(subtask_number))

                subtasks[subtask_number] = SubtaskConfig(
                    subtask_number, config[section_name]
                )
            self._set("subtasks", subtasks)
            self._set("subtask_section_names", subtask_section_names)
        except Exception as e:
            raise RuntimeError("Chyba při načítání configu") from e

        self.check_unused_keys(config)

    def get_maximum_score(self) -> int:
        return sum([subtask.score for subtask in self.subtasks.values()])

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
    def check_unused_keys(self, config: CheckedConfigParser):
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
            assert (
                section_name in accepted_section_names
            ), f"Neočekávaná sekce configu: [{section_name}]"

            if section_name in self.subtask_section_names:
                section_ignored_keys = ignored_keys["subtask"]
            else:
                section_ignored_keys = ignored_keys[section_name]

            for key in config.get_unused_keys(section_name):
                if key not in section_ignored_keys:
                    raise ValueError(
                        f"Neočekávaný klíč '{key}' v sekci [{section_name}] configu."
                    )


class SubtaskConfig(BaseEnv):
    def __init__(
        self, subtask_number: int, config_section: configparser.SectionProxy
    ) -> None:
        super().__init__()
        self._set("name", config_section.get("name", None))
        self._set("score", int(config_section["points"]))
        self._set("in_globs", config_section.get("in_globs", self._all_previous_glob(subtask_number)).split())

    def _all_previous_glob(self, subtask_number):
        return " ".join([f"{util.pad_num(i)}*.in" for i in range(1, subtask_number+1)])

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
