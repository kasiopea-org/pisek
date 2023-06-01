from abc import ABC, abstractmethod
import hashlib
from enum import Enum
from typing import List, Optional, AbstractSet, Callable, Any
import sys

import os.path
from pisek.tests.cache import Cache, CacheEntry
from pisek.env import Env

State = Enum('State', ['in_queue', 'running', 'succeeded', 'failed', 'canceled'])
class PipelineItem(ABC):
    """Generic PipelineItem with state and dependencies."""
    def __init__(self, name : str) -> None:
        self.name = name
        self.state = State.in_queue

        self.prerequisites = 0
        self.required_by = []

    def fail(self, message : str) -> None:
        self.state = State.failed
        return message

    def cancel(self) -> None:
        self.state = State.canceled
        for item in self.required_by:
            item.cancel()

    def check_prerequisites(self) -> None:
        if self.prerequisites > 0:
            raise RuntimeError(f"{self.__class__.__name__} {self.name} prerequisites not finished ({self.prerequisites} remaining).")
    
    def add_prerequisite(self, item) -> None:
        self.prerequisites += 1
        item.required_by.append(self)

    def finish(self) -> None:
        if self.state == State.succeeded:
            for item in self.required_by:
                item.prerequisites -= 1

        elif self.state == State.failed:
            for item in self.required_by:
                item.cancel()

class Job(PipelineItem):
    """One simple cacheable task in pipeline."""
    def __init__(self, name : str, env: Env) -> None:
        self._env = env
        self.result = None
        self._accessed_files = set([])
        super().__init__(name)

    def _access_file(self, filename : str) -> None:
        filename = os.path.normpath(filename)
        self._accessed_files.add(filename)

    def _signature(self, envs: AbstractSet[str], files: AbstractSet[str]) -> Optional[str]:
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
        return CacheEntry(self.name, sign, result, self._env.get_accessed(), list(self._accessed_files))

    def run_job(self, cache: Cache) -> str:
        if self.state == State.canceled:
            return None
        self.check_prerequisites()
        self.state = State.running

        if self.name in cache and self.same_signature(cache[self.name]):
            self.result = cache[self.name]
        else:
            self.result = self._run() 

        if self.state == State.failed:
            print(f"Job '{self.name}' failed:\n{self.result}", file=sys.stderr)
        else:
            cache.add(self.export(self.result))
            self.state = State.succeeded

        return self.result

    @abstractmethod
    def _run(self):
        """What the job actually does (without all the management)."""
        pass


class JobManager(PipelineItem):
    """Object that can create jobs and compute depending on their results."""
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
        """Return status of job manager to be displayed on stdout."""
        return ""

    def finish(self) -> str:
        super().finish()
        return self._get_status()
