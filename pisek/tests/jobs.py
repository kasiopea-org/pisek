from abc import ABC, abstractmethod
import hashlib
from enum import Enum
from typing import List, Dict, AbstractSet, Callable, Any

import os.path
from pisek.tests.cache import Cache, CacheEntry
from pisek.env import Env

State = Enum('State', ['in_queue', 'running', 'succeeded', 'failed', 'canceled'])
class PipelineItem(ABC):
    def __init__(self, name : str):
        self.name = name
        self.state = State.in_queue

        self.prerequisites = 0
        self.required_by = []

    def fail(self, message : str):
        self.state = State.failed
        self.result = message

    def cancel(self):
        self.state = State.canceled
        for item in self.required_by:
            item.cancel()

    def check_prerequisites(self):
        if self.prerequisites > 0:
            raise RuntimeError(f"{self.__class__.__name__} {self.name} prerequisites not finished ({self.prerequisites} remaining).")
    
    def add_prerequisite(self, item):
        self.prerequisites += 1
        item.required_by.append(self)

    def finish(self):
        if self.state == State.succeeded:
            for item in self.required_by:
                item.prerequisites -= 1

        elif self.state == State.failed:
            for item in self.required_by:
                item.cancel()

class Job(PipelineItem):
    def __init__(self, name : str, env: Env) -> None:
        self._env = env
        self.result = None
        self._accessed_files = []
        super().__init__(name)

    def _access_file(self, filename : str) -> Any:
        filename = os.path.normpath(filename)
        if not filename in self._accessed_files:
            self._accessed_files.append(filename)
        return open(filename)

    def _signature(self, envs: AbstractSet[str], files: List[str]):
        sign = hashlib.sha256()
        for variable in sorted(envs):
            sign.update(f"{variable}={self._env.get_without_log(variable)}\n".encode())
        for file in sorted(files):
            with open(file, 'rb') as f:
                file_sign = hashlib.file_digest(f, "sha256")
            sign.update(f"{file}={file_sign.hexdigest()}\n".encode())
        return sign.hexdigest()

    def same_signature(self, cache_entry: CacheEntry) -> bool:
        sign = self._signature(cache_entry.envs, cache_entry.files)
        return cache_entry.signature == sign

    def export(self, result: str) -> CacheEntry:
        sign = self._signature(self._env.get_accessed(), self._accessed_files)
        return CacheEntry(self.name, sign, result, self._env.get_accessed(), self._accessed_files)

    def run_job(self, cache: Cache) -> str:
        if self.state == State.canceled:
            return None
        self.check_prerequisites()
        self.state = State.running

        if self.name in cache and self.same_signature(cache[self.name]):
            self.result = cache[self.name]
        else:
            self.result = self._run() 
            cache.add(self.export(self.result))
        
        self.state = State.succeeded
        return self.result

    @abstractmethod
    def _run(self):
        pass


class JobManager(PipelineItem):
    def create_jobs(self, env: Env) -> List[Job]:
        self.check_prerequisites()
        self.jobs = self._get_jobs(env)
        self.expectations = []
        return self.jobs

    def expect_all(self, jobs, state : State, result : Any):
        self.expect(all, jobs, state, result)

    def expect_any(self, jobs, state : State, result : Any):
        self.expect(any, jobs, state, result)

    def expect(self, what : Callable[[List[bool]], bool], jobs : List[Job], state : State, result : Any) -> Callable[[], bool]:
        def f():
            return what(map(
                lambda j: j.state == state and (result is None or j.result == result),
                jobs
            ))
        self.expectations.append(f)

    @abstractmethod
    def _get_jobs(self, env: Env) -> List[Job]:
        pass

    def update(self) -> str:
        new_state = State.succeeded
        for job in self.jobs:
            if job.state == State.in_queue or job.state == State.running:
                new_state = State.in_queue
                break
            elif job.state == State.failed:
                new_state = State.failed
        self.state = new_state
        
        return self._get_status()

    @abstractmethod
    def _get_status(self) -> str:
        return ""

    def finish(self) -> str:
        super().finish()
        return self._get_status()
