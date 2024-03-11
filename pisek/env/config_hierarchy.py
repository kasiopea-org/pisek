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

from collections import defaultdict
from configparser import ConfigParser
from dataclasses import dataclass
from importlib.resources import files
import os
import re
from typing import Optional, Any

from pisek.utils.text import tab
from pisek.env.config_errors import TaskConfigError
from pisek.env.update_config import update_config

DEFAULTS_CONFIG = str(files("pisek").joinpath("env/global-defaults"))
CONFIG_FILENAME = "config"


@dataclass
class ConfigValue:
    value: Any
    config: str
    section: str
    key: Optional[str]
    internal: bool = False

    def location(self) -> str:
        text = f"section [{self.section}]"
        if self.key is not None:
            text += f", key '{self.key}'"

        if self.internal:
            text += " (internal pisek value)"
        else:
            text += f" (in config file {os.path.abspath(self.config)})"

        return text


class ConfigHierarchy:
    """Represents hierarchy of config files where last overrides all previous."""

    def __init__(self, task_path: str, no_colors: bool = False) -> None:
        self._config_paths = [
            os.path.join(task_path, CONFIG_FILENAME),
            DEFAULTS_CONFIG,
        ]

        self._configs: list[ConfigParser] = []
        for path in self._config_paths:
            self._configs.append(config := ConfigParser())
            if not config.read(path):
                raise TaskConfigError(f"Missing config {path}. Is this task folder?")

        for config in self._configs:
            update_config(config, task_path, no_colors)

        self._used_keys: dict[str, set[str]] = defaultdict(set)

    def get(self, section: str, key: str | None) -> ConfigValue:
        return self.get_from_candidates([(section, key)])

    def get_from_candidates(
        self, candidates: list[tuple[str, str | None]]
    ) -> ConfigValue:
        for section, key in candidates:
            if key is None:
                # Defaultdict, so we are creating the section set
                self._used_keys[section]
            else:
                self._used_keys[section].add(key)

        unset: bool = False
        for config_path, config in zip(self._config_paths, self._configs):
            config_path = os.path.basename(config_path)
            for section, key in candidates:
                if key is None:
                    value = section if section in config else None
                else:
                    value = config.get(section, key, fallback=None)

                if value == "!unset":
                    unset = True
                    break
                elif value is not None:
                    return ConfigValue(
                        value, config_path, section, key
                    )  # TODO: Show config
            if unset:
                break

        def msg(section_key: tuple[str, str | None]) -> str:
            section, key = section_key
            if key is None:
                return f"Section [{section}]"
            else:
                return f"Key '{key}' in section [{section}]"

        candidates_str = " or\n".join(map(msg, candidates))
        raise TaskConfigError(f"Unset value for:\n{tab(candidates_str)}")

    def sections(self) -> list[ConfigValue]:
        sections = {
            section: ConfigValue(section, "", section, None)  # TODO: Add config
            for config in self._configs
            for section in config.sections()
        }  # We need to use dictionary here because order matters
        return list(sections.values())

    def check_unused_keys(self) -> None:
        """
        Check whether lowest config contains unused section or keys.

        Raises
        ------
        TaskConfigError
            If unused sections or keys are present.
        """
        IGNORED_KEYS = defaultdict(
            set,
            {
                "task": {"tests", "version"},  # TODO: Version updates
                "tests": {"in_mode", "out_mode", "out_format", "online_validity"},
            },
        )
        IGNORED_TEST_KEYS = {"file_name"}
        for section in self._configs[0].sections():
            if section not in self._used_keys:
                raise TaskConfigError(f"Unexpected section [{section}] in config")
            for key in self._configs[0][section].keys():
                if key in IGNORED_KEYS[section]:
                    continue
                if (
                    section == "all_tests" or re.match(r"test\d{2}", section)
                ) and key in IGNORED_TEST_KEYS:
                    continue
                if key not in self._used_keys[section]:
                    raise TaskConfigError(
                        f"Unexpected key '{key}' in section [{section}] of config."
                    )

    def check_todos(self) -> bool:
        """Check whether lowest config contains TODO in comments."""
        with open(self._config_paths[0]) as config:
            for line in config:
                if "#" in line and "TODO" in line.split("#")[1]:
                    return True

        return False
