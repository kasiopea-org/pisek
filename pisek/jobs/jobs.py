from abc import ABC, abstractmethod
import hashlib
from enum import Enum
from typing import List, Optional, AbstractSet, Callable, Any
import sys

import os.path
from pisek.jobs.cache import Cache, CacheEntry
from pisek.env import Env

State = Enum('State', ['in_queue', 'running', 'succeeded', 'failed', 'canceled'])
class PipelineItem(ABC):
    """Generic PipelineItem with state and dependencies."""
    def __init__(self, name : str) -> None:
        self.name = name
        self.state = State.in_queue
        self.result = None
        self.fail_msg = ""

        self.prerequisites = 0
        self.required_by = []
        self.prerequisites_results = {}

    def fail(self, message : str) -> None:
        if self.fail_msg != "":
            raise RuntimeError("PipelineItem cannot fail twice.")
        self.state = State.failed
        self.fail_msg = message

    def cancel(self) -> None:
        self.state = State.canceled
        for item in self.required_by:
            item.cancel()

    def check_prerequisites(self) -> None:
        if self.prerequisites > 0:
            raise RuntimeError(f"{self.__class__.__name__} {self.name} prerequisites not finished ({self.prerequisites} remaining).")

    def add_prerequisite(self, item, name: Optional[str] = None) -> None:
        self.prerequisites += 1
        item.required_by.append((self, name))


    def finish(self) -> None:
        if self.state == State.succeeded:
            for item, name in self.required_by:
                item.prerequisites -= 1
                if name is not None:
                    item.prerequisites_results[name] = self.result

        elif self.state == State.failed:
            for item, _ in self.required_by:
                item.cancel()

class Job(PipelineItem):
    """One simple cacheable task in pipeline."""
    def __init__(self, name : str, env: Env) -> None:
        self._env = env.reserve()
        self._accessed_files = set([])
        super().__init__(name)

    def _access_file(self, filename : str) -> None:
        filename = os.path.normpath(filename)
        self._accessed_files.add(filename)

    def _signature(self, envs: List[str], files: AbstractSet[str]) -> Optional[str]:
        sign = hashlib.sha256()
        for variable in sorted(envs):
            sign.update(f"{variable}={self._env.get_without_log(variable)}\n".encode())
        for file in sorted(files):
            if not os.path.exists(file):
                return None
            with open(file, 'rb') as f:
                file_sign = hashlib.file_digest(f, "sha256")
            sign.update(f"{file}={file_sign.hexdigest()}\n".encode())
        return sign.hexdigest()

    def same_signature(self, cache_entry: CacheEntry) -> bool:
        sign = self._signature(cache_entry.envs, cache_entry.files)
        return cache_entry.signature == sign

    def export(self, result: str) -> CacheEntry:
        sign = self._signature(self._env.get_accessed(), self._accessed_files)
        if sign is None:
            raise RuntimeError(
                f"Cannot compute signature of job {self.name}. "
                f"Check if something else is changing files in task directory."
            )
        return CacheEntry(self.name, sign, result, self._env.get_accessed(), list(self._accessed_files))

    def run_job(self, cache: Cache) -> str:
        if self.state == State.canceled:
            return None
        self.check_prerequisites()
        self.state = State.running

        cached = False
        if self.name in cache and self.same_signature(cache[self.name]):
            cached = True
            self.result = cache[self.name].result
        else:
            self.result = self._run()

        if self.state != State.failed:
            if not cached:
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
        if self.state == State.canceled:
            self.jobs = []
        else:
            self.state = State.running
            self._env = env.reserve()
            self.check_prerequisites()
            self.jobs = self._get_jobs()
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

    def _job_states(self):
        return tuple(map(lambda j: j.state, self.jobs))
    
    def _finished_jobs(self):
        return self._job_states().count(State.succeeded)

    def _failed_jobs(self) -> List[Job]:
        return list(filter(lambda j: j.state == State.failed, self.jobs))

    def update(self) -> str:
        states = self._job_states()
        if self.state in (State.failed, State.canceled):
            pass
        elif State.failed in states:
            self.state = State.failed
        else:
            self.state = State.running
 
        return self._get_status()

    @abstractmethod
    def _get_status(self) -> str:
        """Return status of job manager to be displayed on stdout."""
        return ""

    def ready(self) -> bool:
        """
        Returns whether manager is ready for evaluation.
        (i.e. All of it's jobs have finished)
        """
        return self.state == State.running and self._finished_jobs() == len(self.jobs)

    def finish(self) -> str:
        if self.state == State.running:
            self.result = self._evaluate()
            if self.state == State.running:
                self.state = State.succeeded
        super().finish()
        return self._get_status()

    def _evaluate(self) -> Any:
        """Decide whether jobs did run as expected and return result."""
        pass
