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

import time
from typing import Any, Iterable
import os
import pickle

from pisek.version import __version__
from pisek.utils.text import eprint
from pisek.utils.colors import ColorSettings
from pisek.utils.paths import INTERNALS_DIR


CACHE_VERSION_FILE = os.path.join(INTERNALS_DIR, "_pisek_cache_version")
CACHE_CONTENT_FILE = os.path.join(INTERNALS_DIR, "_pisek_cache")
SAVED_LAST_SIGNATURES = 5
CACHE_SAVE_INTERVAL = 1  # seconds


class CacheEntry:
    """Object representing single cached job."""

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


class Cache:
    """Object representing all cached jobs."""

    def __init__(self) -> None:
        os.makedirs(INTERNALS_DIR, exist_ok=True)
        with open(CACHE_VERSION_FILE, "w") as f:
            f.write(f"{__version__}\n")
        self.cache: dict[str, list[CacheEntry]] = {}
        self.last_save = time.time()

    def add(self, cache_entry: CacheEntry):
        """Add entry to cache."""
        if cache_entry.name not in self.cache:
            self.cache[cache_entry.name] = []
        self.cache[cache_entry.name].append(cache_entry)

        # trim number of entries per cache name in order to limit cache size
        self.cache[cache_entry.name] = self.cache[cache_entry.name][
            -SAVED_LAST_SIGNATURES:
        ]

        # Throttling saving saves time massively
        if time.time() - self.last_save > CACHE_SAVE_INTERVAL:
            self.export()
            self.last_save = time.time()

    def __contains__(self, name: str) -> bool:
        return name in self.cache

    def __getitem__(self, name: str) -> list[CacheEntry]:
        return self.cache[name]

    def entry_names(self) -> list[str]:
        return list(self.cache.keys())

    def last_entry(self, name: str) -> CacheEntry:
        return self[name][-1]

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
        with open(CACHE_CONTENT_FILE, "wb") as f:
            pickle.dump(self, f)


def load_cache() -> Cache:
    """Load cache file."""
    if not os.path.exists(CACHE_VERSION_FILE) or not os.path.exists(CACHE_CONTENT_FILE):
        return Cache()

    with open(CACHE_VERSION_FILE) as f:
        version = f.read().strip()

    if version != __version__:
        eprint(
            ColorSettings.colored(
                "Different version of .pisek_cache file found. Starting from scratch...",
                "yellow",
            )
        )
        return Cache()

    with open(CACHE_CONTENT_FILE, "rb") as f:
        cache: Cache = pickle.load(f)

    return cache
