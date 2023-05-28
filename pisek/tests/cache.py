from typing import List, Dict, Any
import os
import yaml

CACHE_FILENAME = ".pisek_cache"
SAVED_LAST_SIGNATURES = 5

class CacheEntry(yaml.YAMLObject):
    yaml_tag = u'!Entry'
    def __init__(self, name: str, signature: str, result: str, envs: List[str], files: List[str]) -> None:
        self.name = name
        self.signature = signature
        self.result = result
        self.envs = envs
        self.files = files

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, signature={self.signature}" \
               f"result={self.result}, envs={self.envs}, files={self.files})"

    def yaml_export(self) -> str:
        return yaml.dump([self])

class Cache:
    def __init__(self, env) -> None:
        self.cache_path = os.path.join(env.task_dir, CACHE_FILENAME)
        self.cache = self._load()

    def add(self, cache_entry: CacheEntry):
        self.cache[cache_entry.name] = cache_entry
        with open(self.cache_path, 'a') as f:
            f.write(cache_entry.yaml_export())

    def __contains__(self, name: str) -> bool:
        return name in self.cache

    def __getitem__(self, name: str) -> CacheEntry:
        return self.cache[name]

    def _load(self) -> Dict[str, CacheEntry]:
        if not os.path.exists(self.cache_path):
            return {}

        cache = {}
        with open(self.cache_path) as f:
            entries = yaml.full_load(f)
            if entries is None:
                return {}
            for entry in entries:
                cache[entry.name] = entry

        return cache
