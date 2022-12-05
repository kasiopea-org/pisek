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

CONFIG_FILENAME = "config"
DATA_SUBDIR = "data/"


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


class TaskConfig:
    def __init__(self, task_dir: str) -> None:
        config = CheckedConfigParser()
        config_path = os.path.join(task_dir, CONFIG_FILENAME)
        read_files = config.read(config_path)
        self.task_dir = task_dir

        if not read_files:
            raise FileNotFoundError(
                f"Chybí konfigurační soubor {config_path}, je toto složka s úlohou?"
            )

        try:
            self.solutions: List[str] = config.get("task", "solutions").split()
            self.contest_type = config["task"].get("contest_type", "kasiopea")
            self.generator: str = config["tests"]["in_gen"]
            self.checker: Optional[str] = config["tests"].get("checker")
            self.judge_type: str = config["tests"].get("out_check", "diff")
            self.judge_name: Optional[str] = None
            if self.judge_type == "judge":
                self.judge_name = config["tests"]["out_judge"]

            # Relevant for CMS interactive tasks. The file to be linked with
            # the contestant's solution (primarily for C++)
            self.solution_manager: str = config["tests"].get("solution_manager")
            if self.solution_manager:
                self.solution_manager = os.path.join(
                    self.task_dir, self.solution_manager
                )

            if self.contest_type == "cms":
                # Warning: these timeouts are currently ignored in Kasiopea!
                self.timeout_model_solution: Optional[float] = apply_to_optional(
                    config.get("limits", "solve_time_limit", fallback=None), float
                )
                self.timeout_other_solutions: Optional[float] = apply_to_optional(
                    config.get("limits", "sec_solve_time_limit", fallback=None), float
                )

            # Support for different directory structures
            self.samples_subdir: str = config["task"].get("samples_subdir", ".")
            self.data_subdir: str = config["task"].get("data_subdir", DATA_SUBDIR)

            if "solutions_subdir" in config["task"]:
                # Prefix each solution name with solutions_subdir/
                subdir = config["task"].get("solutions_subdir", ".")
                self.solutions = [os.path.join(subdir, sol) for sol in self.solutions]

            self.subtasks: Dict[int, SubtaskConfig] = {}
            self.subtask_section_names = set()

            for section_name in config.sections():
                m = re.match(r"test([0-9]{2})", section_name)

                if not m:
                    # One of the other sections ([task], [tests]...)
                    continue

                self.subtask_section_names.add(section_name)

                n = int(m.groups()[0])
                if n in self.subtasks:
                    raise ValueError("Duplicate subtask number {}".format(n))

                self.subtasks[n] = SubtaskConfig(
                    self.contest_type, config[section_name]
                )
        except Exception as e:
            raise RuntimeError("Chyba při načítání configu") from e

        self.check_unused_keys(config)

    def get_maximum_score(self) -> int:
        return sum([subtask.score for subtask in self.subtasks.values()])

    def get_data_dir(self):
        return os.path.join(self.task_dir, self.data_subdir)

    def get_samples_dir(self):
        return os.path.join(self.task_dir, self.samples_subdir)

    def __repr__(self):
        return "<TaskConfig %s>" % ", ".join(
            f"{k} = {getattr(self, k)}"
            for k in filter(
                lambda k: not k.startswith("_") and not callable(getattr(self, k)),
                dir(self),
            )
        )

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
            "task": {"name", "tests"},
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


class SubtaskConfig:
    def __init__(
        self, contest_type: str, config_section: configparser.SectionProxy
    ) -> None:
        self.name: Optional[str] = config_section.get("name", None)
        self.score: int = int(config_section["points"])

        if contest_type == "cms":
            self.in_globs: List[str] = config_section["in_globs"].split()

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
