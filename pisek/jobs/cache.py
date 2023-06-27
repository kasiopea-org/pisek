from enum import Enum
from typing import Any
import os
import yaml

CACHE_FILENAME = ".pisek_cache"
SAVED_LAST_SIGNATURES = 5

class CacheResultEnum:
    """Enum of strings."""
    def __init__(self, *values):
        self.values = values
        for value in values:
            setattr(self, value, value)

    def __iter__(self):
        yield from self.values

class CacheEntry(yaml.YAMLObject):
    """Object representing single cached job."""
    yaml_tag = u'!Entry'
    def __init__(self, name: str, signature: str, result: str, envs: list[str], files: list[str], results: list[Any]) -> None:
        self.name = name
        self.signature = signature
        self.result = result
        self.envs = list(sorted(envs))
        self.files = list(sorted(files))
        self.prerequisites_results = sorted(list(results))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, signature={self.signature}, " \
               f"result={self.result}, envs={self.envs}, files={self.files}, " \
               f"prerequisites_results={self.prerequisites_results})"

    def yaml_export(self) -> str:
        return yaml.dump([self], allow_unicode=True)

class Cache:
    """Object representing all cached jobs."""
    def __init__(self, env) -> None:
        self.cache_path = os.path.join(env.task_dir, CACHE_FILENAME)
        self.cache = self._load()

    def add(self, cache_entry: CacheEntry):
        """Add entry to cache."""
        self.cache[cache_entry.name] = cache_entry
        with open(self.cache_path, 'a', encoding='utf-8') as f:
            f.write(cache_entry.yaml_export())

    def __contains__(self, name: str) -> bool:
        return name in self.cache

    def __getitem__(self, name: str) -> CacheEntry:
        return self.cache[name]

    def _load(self) -> dict[str, CacheEntry]:
        """Load cache file."""
        if not os.path.exists(self.cache_path):
            return {}

        cache = {}
        with open(self.cache_path, encoding='utf-8') as f:
            entries = yaml.full_load(f)
            if entries is None:
                return {}
            for entry in entries:
                cache[entry.name] = entry

        return cache

    def export(self) -> None:
        """Export cache into a file."""
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            for cache_entry in self.cache.values():
                f.write(cache_entry.yaml_export())
