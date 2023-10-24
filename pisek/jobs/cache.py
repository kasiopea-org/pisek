# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
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

from typing import Any
import os
import yaml

CACHE_FILENAME = ".pisek_cache"
SAVED_LAST_SIGNATURES = 5


class CacheEntry(yaml.YAMLObject):
    """Object representing single cached job."""

    yaml_tag = "!Entry"

    def __init__(
        self,
        name: str,
        signature: str,
        result: Any,
        envs: list[str],
        files: list[str],
        results: list[Any],
    ) -> None:
        self.name = name
        self.signature = signature
        self.result = result
        self.prerequisites_results = sorted(list(results))
        self.envs = list(sorted(envs))
        self.files = list(sorted(files))

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name={self.name}, signature={self.signature}, "
            f"result={self.result}, prerequisites_results={self.prerequisites_results}, "
            f"envs={self.envs}, files={self.files})"
        )

    def yaml_export(self) -> str:
        return yaml.dump([self], allow_unicode=True, sort_keys=False)


class CacheSeal(yaml.YAMLObject):
    """Seal is stored after last entry containing data about run."""

    yaml_tag = "!Seal"

    def __init__(self, success: bool, msg: str = ""):
        self.success = success
        self.msg = msg

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(success={self.success}, msg={self.msg})"

    def yaml_export(self) -> str:
        return yaml.dump([self], allow_unicode=True, sort_keys=False)


class Cache:
    """Object representing all cached jobs."""

    def __init__(self, env) -> None:
        self.cache_path = os.path.join(env.task_dir, CACHE_FILENAME)
        self.broken_seal = None
        self._load()

    def add(self, cache_entry: CacheEntry):
        """Add entry to cache."""
        if cache_entry.name not in self.cache:
            self.cache[cache_entry.name] = []
        self.cache[cache_entry.name].append(cache_entry)

        with open(self.cache_path, "a", encoding="utf-8") as f:
            f.write(cache_entry.yaml_export())

    def __contains__(self, name: str) -> bool:
        return name in self.cache

    def __getitem__(self, name: str) -> list[CacheEntry]:
        return self.cache[name]

    def entry_names(self) -> list[str]:
        return list(self.cache.keys())

    def last_entry(self, name: str) -> CacheEntry:
        return self[name][-1]

    def _load(self) -> None:
        """Load cache file."""
        self.cache = {}
        if not os.path.exists(self.cache_path):
            return

        with open(self.cache_path, encoding="utf-8") as f:
            entries = yaml.full_load(f)
            if entries is None:
                return
            for entry in entries:
                if isinstance(entry, CacheSeal):
                    self.broken_seal = entry
                    break
                if entry.name not in self.cache:
                    self.cache[entry.name] = []
                self.cache[entry.name].append(entry)

        self.export()  # Break the CacheSeal

    def move_to_top(self, entry: CacheEntry):
        """Move given entry to most recent position."""
        if entry in self.cache[entry.name]:
            self.cache[entry.name].remove(entry)
        else:
            raise ValueError(
                f"Cannot move to top entry which is not in Cache:\n{entry}"
            )
        self.add(entry)

    def export(self) -> None:
        """Export cache into a file. Remove unnecessary entries and add seal."""
        with open(self.cache_path, "w", encoding="utf-8") as f:
            for job, entries in self.cache.items():
                for cache_entry in entries[-SAVED_LAST_SIGNATURES:]:
                    f.write(cache_entry.yaml_export())

    def seal(self, success):
        self.export()
        with open(self.cache_path, "a", encoding="utf-8") as f:
            f.write(CacheSeal(success).yaml_export())
