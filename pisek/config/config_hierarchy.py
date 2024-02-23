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
from importlib.resources import files
import os

from pisek.config.config_errors import TaskConfigError
from pisek.terminal import tab

DEFAULTS_CONFIG = files("pisek").joinpath("defaults-config")


# TODO: Version update


class TaskConfigParser(configparser.RawConfigParser):
    """
    https://stackoverflow.com/questions/57305229/python-configparser-get-list-of-unused-entries
    ConfigParser that tracks unused keys.
    """

    used_vars: dict[str, set] = {}

    def get_unused_keys(self, section):
        all_options = self.options(section)

        # We need the default in case the section is not present at all.
        section_used_vars = self.used_vars.get(section, [])

        unused_options = [x for x in all_options if x not in section_used_vars]
        return unused_options

    def get(self, section: str, option: str, *args, **kwargs):
        if section not in self.used_vars:
            self.used_vars[section] = set([option])
        else:
            self.used_vars[section].add(option)

        return super().get(section, option, *args, **kwargs)

    # def check_unused_keys(self, config: TaskConfigParser) -> None:
    #     """Verify that there are no unused keys in the config, raise otherwise."""

    #     accepted_section_names = (
    #         self._subtask_section_names
    #         | self._solution_section_names
    #         | {
    #             "task",
    #             "tests",
    #             "limits",
    #         }
    #     )

    #     # These keys are accepted for backwards compatibility reasons because the config
    #     # format is based on KSP's opendata tool.
    #     ignored_keys = {
    #         "task": {"tests"},
    #         "tests": {"in_mode", "out_mode", "out_format", "online_validity"},
    #         "limits": {},
    #         # Any subtask section like "test01", "test02"...
    #         "subtask": {"file_name"},
    #         # Any solution section like solution_solve, solution_slow, ...
    #         "solution": {},
    #     }

    #     for section_name in config.sections():
    #         if not section_name in accepted_section_names:
    #             raise TaskConfigError(f"Unexpected section [{section_name}] in config")

    #         if section_name in self._subtask_section_names:
    #             section_ignored_keys = ignored_keys["subtask"]
    #         elif section_name in self._solution_section_names:
    #             section_ignored_keys = ignored_keys["solution"]
    #         else:
    #             section_ignored_keys = ignored_keys[section_name]

    #         for key in config.get_unused_keys(section_name):
    #             if key not in section_ignored_keys:
    #                 raise TaskConfigError(
    #                     f"Unexpected key '{key}' in section [{section_name}] of config."
    #                 )

    #     return None


class ConfigHierarchy:
    def __init__(self, task_path: str) -> None:
        self._config_path = os.path.join(task_path, "config")
        config_paths = [DEFAULTS_CONFIG, self._config_path]
        self._configs = [TaskConfigParser() for _ in config_paths]
        for config, path in zip(self._configs, config_paths):
            if not config.read(path):
                raise TaskConfigError(f"Missing config {path}. Is this task folder?")

    def get(self, section: str, key: str) -> str:
        return self.get_from_candidates([(section, key)])

    def get_from_candidates(self, candidates: list[tuple[str, str]]):
        for config in reversed(self._configs):
            for section, key in candidates:
                value = config.get(section, key, fallback=None)
                if value == "!unset":
                    break
                elif value is not None:
                    return value
        
        def msg(section_key: tuple[str, str]) -> str:
            return f"key '{section_key[1]}' in section [{section_key[0]}]"
        
        candidates_str = "or \n".join(map(msg, candidates))
        raise TaskConfigError(f"Unset value for:\n{tab(candidates_str)}")

    def check_todos(self) -> bool:
        """Check whether config contains TODO in comments."""
        with open(self._config_path) as config:
            for line in config:
                if "#" in line and "TODO" in line.split("#")[1]:
                    return True

        return False

    def sections(self):
        sections = {
            section: True for config in self._configs for section in config.sections()
        }
        return list(sections.keys())
