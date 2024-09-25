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
from configparser import (
    ConfigParser,
    DuplicateSectionError,
    DuplicateOptionError,
    MissingSectionHeaderError,
)
from dataclasses import dataclass
from importlib.resources import files
import os
from typing import Optional, Iterable

from pisek.utils.text import tab

from .config_errors import TaskConfigError, TaskConfigParsingError
from .update_config import update_config
from .did_you_mean import ConfigKeysHelper

GLOBAL_DEFAULTS = str(files("pisek").joinpath("config/global-defaults"))
V2_DEFAULTS = {
    task_type: str(files("pisek").joinpath(f"config/{task_type}-defaults"))
    for task_type in ["kasiopea", "cms"]
}

CONFIG_FILENAME = "config"


@dataclass
class ConfigValue:
    value: str
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

    def __init__(
        self,
        task_path: str,
        info: bool = True,
        pisek_directory: Optional[str] = None,
    ) -> None:
        self._task_path = task_path
        self._pisek_directory = pisek_directory

        self._config_paths: list[str] = []
        self._configs: list[ConfigParser] = []

        self._load_config(os.path.join(task_path, CONFIG_FILENAME), info)
        self._load_config(GLOBAL_DEFAULTS, False)

        self._used_keys: dict[str, set[str]] = defaultdict(set)

    def _load_config(self, path: str, info: bool = True) -> None:
        self._config_paths.append(path)
        self._configs.append(config := ConfigParser())
        if not self._read_config(config, path):
            raise TaskConfigError(f"Missing config {path}. Is this task folder?")

        update_config(config, self._task_path, info)
        if defaults := config.get("task", "use", fallback=None):
            self._load_config(self._resolve_defaults_config(defaults), False)

    def _read_config(self, config: ConfigParser, path: str) -> bool:
        try:
            res = config.read(path)
        except DuplicateSectionError as e:
            raise TaskConfigParsingError(path, f"Duplicate section [{e.section}]")
        except DuplicateOptionError as e:
            raise TaskConfigParsingError(
                path, f"Duplicate key '{e.option}' in section [{e.section}]"
            )
        except MissingSectionHeaderError as e:
            raise TaskConfigParsingError(path, f"Missing section header")
        return len(res) > 0

    def _resolve_defaults_config(self, name: str):
        def load_from_path(path: str) -> str:
            configs_folder = os.path.join(path, "configs")
            if not os.path.exists(configs_folder):
                raise TaskConfigError(f"'{configs_folder}' does not exist.")
            defaults = os.path.join(configs_folder, name)
            if not os.path.exists(defaults):
                raise TaskConfigError(
                    f"Config '{name}' does not exist in: '{configs_folder}'"
                )
            return defaults

        if name.startswith("@"):
            if (default := V2_DEFAULTS.get(name.removeprefix("@"))) is None:
                raise TaskConfigError(f"Unknown special task_type: '{name}'")
            return default

        if self._pisek_directory is not None:
            return load_from_path(os.path.join(self._task_path, self._pisek_directory))

        if "PISEK_DIRECTORY" in os.environ:
            return load_from_path(
                os.path.join(self._task_path, os.environ["PISEK_DIRECTORY"])
            )

        current_path = os.path.abspath(self._task_path)
        while current_path:
            if os.path.exists(os.path.join(current_path, ".git")):
                return load_from_path(os.path.join(current_path, "pisek"))
            step_up = os.path.abspath(os.path.join(current_path, ".."))
            if step_up == current_path:
                break  # topmost directory
            if os.stat(step_up).st_uid != os.stat(current_path).st_uid:
                break  # other user's directory
            current_path = step_up

        return name

    def get(self, section: str, key: str | None) -> ConfigValue:
        return self.get_from_candidates([(section, key)])

    def get_from_candidates(
        self, candidates: Iterable[tuple[str, str | None]]
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
                    return ConfigValue(value, config_path, section, key)
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
            section: ConfigValue(section, path, section, None)
            for config, path in reversed(list(zip(self._configs, self._config_paths)))
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
        IGNORED_KEYS = defaultdict(set, {"task": {"version", "use"}})
        self._config_helper = ConfigKeysHelper()
        for section in self._configs[0].sections():
            if section not in self._used_keys:
                raise TaskConfigError(
                    f"Unexpected section [{section}] in config. "
                    f"(Did you mean [{self._config_helper.find_section(section)}]?)"
                )
            for key in self._configs[0][section].keys():
                if key in IGNORED_KEYS[section]:
                    continue
                if key not in self._used_keys[section]:
                    help_msg = self._help_invalid_key(section, key)
                    raise TaskConfigError(
                        f"Unexpected key '{key}' in section [{section}] of config."
                        + (f" {help_msg}" if help_msg else "")
                    )

    def check_todos(self) -> bool:
        """Check whether lowest config contains TODO in comments."""
        with open(self._config_paths[0]) as config:
            for line in config:
                if "#" in line and "TODO" in line.split("#")[1]:
                    return True

        return False

    def _help_invalid_key(self, section: str, key: str) -> str:
        guess = self._config_helper.find_key(section, key, self)
        if guess is None:
            return ""

        return (
            f"(Did you mean '{guess[1]}'"
            + (f" in section [{guess[0]}]" if section != guess[0] else "")
            + "?)"
        )
