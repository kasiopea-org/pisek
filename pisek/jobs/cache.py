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

from typing import Any, Iterable, TextIO
import os
import yaml

from pisek.version import __version__
from pisek.utils.text import eprint
from pisek.utils.colors import ColorSettings
from pisek.env.env import Env

CACHE_FILENAME = ".pisek_cache"
SAVED_LAST_SIGNATURES = 5


class CacheInfo(yaml.YAMLObject):
    """Object for cache metadata."""

    yaml_tag = "!Info"

    def __init__(self, version: str = __version__) -> None:
        self.version = version

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(version={self.version})"

    @staticmethod
    def read(f: TextIO) -> "CacheInfo":
        tag = f.readline().removeprefix("- ").strip()
        if tag != CacheInfo.yaml_tag:
            return CacheInfo("?.?.?")
        version = f.readline().removeprefix("  version:").strip()
        return CacheInfo(version)

    def yaml_export(self) -> str:
        return yaml.dump([self], allow_unicode=True, sort_keys=False)


class CacheEntry(yaml.YAMLObject):
    """Object representing single cached job."""

    yaml_tag = "!Entry"

    def __init__(
        self,
        name: str,
        signature: str,
        result: Any,
        envs: Iterable[str],
        files: Iterable[str],
        prerequisites_results: Iterable[str],
        output: list[tuple[str, bool]],
    ) -> None:
        self.name = name
        self.signature = signature
        self.result = result
        self.prerequisites_results = list(sorted(prerequisites_results))
        self.envs = list(sorted(envs))
        self.files = list(sorted(files))
        self.output = output

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name={self.name}, signature={self.signature}, "
            f"result={self.result}, prerequisites_results={self.prerequisites_results}, "
            f"envs={self.envs}, files={self.files}, output={self.output})"
        )

    def yaml_export(self) -> str:
        return yaml.dump([self], allow_unicode=True, sort_keys=False)


class Cache:
    """Object representing all cached jobs."""

    def __init__(self, env: Env) -> None:
        self._load(env)

    def _new_cache_file(self) -> None:
        """Create new cache file with metadata."""
        with open(CACHE_FILENAME, "w", encoding="utf-8") as f:
            f.write(CacheInfo().yaml_export())

    def add(self, cache_entry: CacheEntry):
        """Add entry to cache."""
        if cache_entry.name not in self.cache:
            self.cache[cache_entry.name] = []
        self.cache[cache_entry.name].append(cache_entry)

        with open(CACHE_FILENAME, "a", encoding="utf-8") as f:
            f.write(cache_entry.yaml_export())

    def __contains__(self, name: str) -> bool:
        return name in self.cache

    def __getitem__(self, name: str) -> list[CacheEntry]:
        return self.cache[name]

    def entry_names(self) -> list[str]:
        return list(self.cache.keys())

    def last_entry(self, name: str) -> CacheEntry:
        return self[name][-1]

    def _load(self, env: Env) -> None:
        """Load cache file."""
        self.cache: dict[str, list[CacheEntry]] = {}
        if not os.path.exists(CACHE_FILENAME):
            return self._new_cache_file()

        with open(CACHE_FILENAME, encoding="utf-8") as f:
            if CacheInfo.read(f).version != __version__:
                eprint(
                    ColorSettings.colored(
                        "Different version of .pisek_cache file found. Starting from scratch...",
                        "yellow",
                    )
                )
                return self._new_cache_file()

            entries = yaml.full_load(f)
            for entry in entries:
                if entry.name not in self.cache:
                    self.cache[entry.name] = []
                self.cache[entry.name].append(entry)

    def move_to_top(self, entry: CacheEntry):
        """Move given entry to most recent position."""
        if entry in self.cache[entry.name]:
            self.cache[entry.name].remove(entry)
            self.cache[entry.name].append(entry)
        else:
            raise ValueError(
                f"Cannot move to top entry which is not in Cache:\n{entry}"
            )

    def export(self) -> None:
        """Export cache into a file. (Removes unnecessary entries.)"""
        with open(CACHE_FILENAME, "w", encoding="utf-8") as f:
            f.write(CacheInfo().yaml_export())
            for job, entries in self.cache.items():
                for cache_entry in entries[-SAVED_LAST_SIGNATURES:]:
                    f.write(cache_entry.yaml_export())
