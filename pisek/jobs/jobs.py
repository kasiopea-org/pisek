from abc import ABC, abstractmethod
import hashlib
from enum import Enum
from typing import Optional, AbstractSet, Callable, Any
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

    def _fail(self, message : str) -> None:
        if self.fail_msg != "":
            raise RuntimeError("PipelineItem cannot fail twice.")
        self.state = State.failed
        self.fail_msg = message

    def cancel(self) -> None:
        """Cancels job and all that require it."""
        if self.state == State.canceled:
            return  # Canceled already
        self.state = State.canceled
        for item, _ in self.required_by:
            item.cancel()

    def _check_prerequisites(self) -> None:
        """Checks if all prerequisites are finished raises error otherwise."""
        if self.prerequisites > 0:
            raise RuntimeError(f"{self.__class__.__name__} {self.name} prerequisites not finished ({self.prerequisites} remaining).")

    def add_prerequisite(self, item, name: Optional[str] = None) -> None:
        """Adds given PipelineItem as a prerequisite to this job."""
        self.prerequisites += 1
        item.required_by.append((self, name))

    def finish(self) -> None:
        """Notifies PipelineItems that depend on this job."""
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
        """Add file this job depends on."""
        filename = os.path.normpath(filename)
        self._accessed_files.add(filename)

    def _signature(self, envs: list[str], files: AbstractSet[str], results: dict[Any]) -> tuple[Optional[str]]:
        """Compute a signature (i.e. hash) of given envs, files and prerequisites results. """
        sign = hashlib.sha256()
        for variable in sorted(envs):
            if variable not in self._env:
                return (None, "Env nonexistent")
            sign.update(f"{variable}={self._env.get_without_log(variable)}\n".encode())
        for file in sorted(files):
            if not os.path.exists(file):
                return (None, "File nonexistent")
            with open(file, 'rb') as f:
                file_sign = hashlib.file_digest(f, "sha256")
            sign.update(f"{file}={file_sign.hexdigest()}\n".encode())
        for name, result in sorted(results.items()):
            sign.update(f"{name}={result}".encode())
        return (sign.hexdigest(), None)

    def _same_signature(self, cache_entry: CacheEntry) -> bool:
        """Checks whether this job has a same signature as a corresponding CacheEntry."""
        sign, err = self._signature(cache_entry.envs, cache_entry.files, self.prerequisites_results)
        return cache_entry.signature == sign

    def _export(self, result: str) -> CacheEntry:
        """Export this job into CacheEntry."""
        sign, err = self._signature(self._env.get_accessed(), self._accessed_files, self.prerequisites_results)
        if err == "File nonexistent":
            raise RuntimeError(
                f"Cannot compute signature of job {self.name}. "
                f"Check if something else is changing files in task directory."
            )
        return CacheEntry(
            self.name,
            sign,
            result,
            self._env.get_accessed(),
            list(self._accessed_files),
            list(self.prerequisites_results)
        )

    def run_job(self, cache: Cache) -> str:
        """Run this job. If result is already in cache use it instead."""
        if self.state == State.canceled:
            return None
        self._check_prerequisites()
        self.state = State.running

        cached = False
        if self.name in cache and self._same_signature(cache[self.name]):
            cached = True
            self.result = cache[self.name].result
        else:
            self.result = self._run()

        if self.state != State.failed:
            if not cached:
                cache.add(self._export(self.result))
            self.state = State.succeeded

        return self.result

    @abstractmethod
    def _run(self):
        """What this job actually does (without all the management)."""
        pass


class JobManager(PipelineItem):
    """Object that can create jobs and compute depending on their results."""
    def create_jobs(self, env: Env) -> list[Job]:
        """Crates this JobManager's jobs."""
        if self.state == State.canceled:
            self.jobs = []
        else:
            self.state = State.running
            self._env = env.reserve()
            self._check_prerequisites()
            self.jobs = self._get_jobs()
            self.expectations = []
        return self.jobs

    @abstractmethod
    def _get_jobs(self, env: Env) -> list[Job]:
        """Actually creates this JobManager's jobs (without management)."""
        pass

    def _job_states(self) -> tuple[State]:
        """States of this manager's jobs."""
        return tuple(map(lambda j: j.state, self.jobs))
    
    def _jobs_with_state(self, state: State) -> list[Job]:
        return list(filter(lambda j: j.state == state, self.jobs))

    def update(self) -> str:
        """Update this manager's state according to its jobs and return status."""
        states = self._job_states()
        if self.state in (State.failed, State.canceled):
            pass
        elif State.in_queue in states or State.running in states:
            self.state = State.running
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
        return self.state == State.running and len(self._jobs_with_state(State.succeeded)) == len(self.jobs)

    def any_failed(self) -> bool:
        """Returns whether this manager or its jobs had any failures so far."""
        return self.state == State.failed or len(self._jobs_with_state(State.failed))

    def finish(self) -> str:
        """Finishes this JobManager - Does final evaluation and returns final status."""

        if self.state == State.running:
            self.result = self._evaluate()
            if self.state == State.running:
                self.state = State.succeeded
        super().finish()
        return self._get_status()

    def _evaluate(self) -> Any:
        """Decide whether jobs did run as expected and return result."""
        pass
