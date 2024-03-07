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

from abc import ABC, abstractmethod
from copy import deepcopy
import hashlib
from enum import Enum
from functools import wraps
import sys
from typing import Optional, AbstractSet, MutableSet, Any
import yaml

import os.path
from pisek.jobs.cache import Cache, CacheEntry
from pisek.env.env import Env
from pisek.paths import TaskPath

State = Enum("State", ["in_queue", "running", "succeeded", "failed", "canceled"])


class PipelineItemFailure(Exception):
    pass


class CaptureInitParams:
    """
    Class that stores __init__ args and kwargs of its descendants
    and forks and locks Env given to it. Only does that to the topmost __init__.
    """

    _initialized = False

    def __init_subclass__(cls):
        real_init = cls.__init__

        @wraps(real_init)
        def wrapped_init(self, env: Env, *args, **kwargs):
            if not self._initialized:
                self._args = args
                self._kwargs = kwargs
                self._initialized = True
                self._env = env.fork()
                self._env.lock()
            real_init(self, self._env, *args, **kwargs)

        cls.__init__ = wrapped_init


class PipelineItem(ABC):
    """Generic PipelineItem with state and dependencies."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.state = State.in_queue
        self.result: Optional[Any] = None
        self.fail_msg = ""
        self.dirty = False  # Prints something to console?

        self.prerequisites = 0
        self.required_by: list[tuple["PipelineItem", Optional[str]]] = []
        self.prerequisites_results: dict[str, Any] = {}

    def _print(self, msg: str, end: str = "\n", stderr: bool = False) -> None:
        """Prints text to stdout/stderr."""
        self.dirty = True
        (sys.stderr if stderr else sys.stdout).write(msg + end)

    def _fail(self, failure: PipelineItemFailure) -> None:
        """End this job in failure."""
        if self.fail_msg != "":
            raise RuntimeError("PipelineItem cannot fail twice.")
        self.state = State.failed
        self.fail_msg = str(failure)

    def cancel(self) -> None:
        """Cancels job and all that require it."""
        if self.state in (State.succeeded, State.canceled):
            return  # No need to cancel
        self.state = State.canceled
        for item, _ in self.required_by:
            item.cancel()

    def _check_prerequisites(self) -> None:
        """Checks if all prerequisites are finished raises error otherwise."""
        if self.prerequisites > 0:
            raise RuntimeError(
                f"{self.__class__.__name__} {self.name} prerequisites not finished ({self.prerequisites} remaining)."
            )

    def add_prerequisite(
        self, item: "PipelineItem", name: Optional[str] = None
    ) -> None:
        """Adds given PipelineItem as a prerequisite to this job."""
        self.prerequisites += 1
        item.required_by.append((self, name))

    def finish(self) -> None:
        """Notifies PipelineItems that depend on this job."""
        if self.state == State.succeeded:
            for item, name in self.required_by:
                item.prerequisites -= 1
                if name is not None:
                    item.prerequisites_results[name] = deepcopy(self.result)

        elif self.state == State.failed:
            for item, _ in self.required_by:
                item.cancel()


class Job(PipelineItem, CaptureInitParams):
    """One simple cacheable task in pipeline."""

    _args: list[Any]
    _kwargs: dict[str, Any]

    def __init__(self, env: Env, name: str) -> None:
        self._env = env
        self._accessed_files: MutableSet[str] = set([])
        self._terminal_output: list[tuple[str, bool]] = []
        self.name = name
        super().__init__(name)

    def _print(self, msg: str, end: str = "\n", stderr: bool = False) -> None:
        """Prints text to stdout/stderr and caches it."""
        self._terminal_output.append((msg + end, stderr))
        return super()._print(msg, end, stderr)

    def _access_file(self, filename: TaskPath) -> None:
        """Add file this job depends on."""
        self._accessed_files.add(filename.path)

    def _signature(
        self, envs: AbstractSet[str], paths: AbstractSet[str], results: dict[str, Any]
    ) -> tuple[Optional[str], Optional[str]]:
        """Compute a signature (i.e. hash) of given envs, files and prerequisites results."""
        sign = hashlib.sha256()
        for i, arg in enumerate(self._args):
            sign.update(f"{i}={arg}\n".encode())
        for key, val in self._kwargs.items():
            sign.update(f"{key}={val}\n".encode())

        for key in sorted(envs):
            try:
                value = self._env.get_compound(key)
            except (AttributeError, TypeError):
                return (None, f"Key nonexistent: {key}")
            sign.update(f"{key}={value}\n".encode())

        expanded_files = []
        for path in sorted(paths):
            if os.path.isfile(path):
                expanded_files.append(path)
            else:
                for dir_, _, dir_files in os.walk(path):
                    for path in dir_files:
                        expanded_files.append(os.path.join(dir_, path))

        for file in sorted(expanded_files):
            if not os.path.exists(file):
                return (None, "File nonexistent")
            with open(file, "rb") as f:
                file_sign = hashlib.file_digest(f, "sha256")
            sign.update(f"{file}={file_sign.hexdigest()}\n".encode())

        for name, result in sorted(results.items()):
            sign.update(f"{name}={yaml.dump(result)}".encode())

        return (sign.hexdigest(), None)

    def _find_entry(self, cache_entries: list[CacheEntry]) -> Optional[CacheEntry]:
        """Finds a corresponding CacheEntry for this Job."""
        for cache_entry in cache_entries:
            sign, err = self._signature(
                set(cache_entry.envs),
                set(cache_entry.files),
                self.prerequisites_results,
            )
            if cache_entry.signature == sign:
                return cache_entry
        return None

    def _export(self, result: Any) -> CacheEntry:
        """Export this job into CacheEntry."""
        sign, err = self._signature(
            set(self._env.get_accessed()),
            self._accessed_files,
            self.prerequisites_results,
        )
        if err == "File nonexistent":
            raise RuntimeError(
                f"Cannot compute signature of job {self.name}. "
                f"Check if something else is changing files in task directory."
            )
        elif sign is None:
            raise RuntimeError(
                f"Computing signature of job {self.name} failed:\n  {err}."
            )
        return CacheEntry(
            self.name,
            sign,
            result,
            self._env.get_accessed(),
            list(self._accessed_files),
            list(self.prerequisites_results),
            self._terminal_output,
        )

    def run_job(self, cache: Cache) -> None:
        """Run this job. If result is already in cache use it instead."""
        if not self._initialized:
            raise RuntimeError(
                "Job must be initialized before running it. (call Job.init)"
            )
        if self.state == State.canceled:
            return None
        self._check_prerequisites()
        self.state = State.running

        cached = False
        if self.name in cache and (entry := self._find_entry(cache[self.name])):
            cached = True
            cache.move_to_top(entry)
            for msg, stderr in entry.output:
                self._print(msg, end="", stderr=stderr)
            self.result = entry.result
        else:
            try:
                self.result = self._run()
            except PipelineItemFailure as failure:
                self._fail(failure)

        if self.state != State.failed:
            if not cached:
                cache.add(self._export(self.result))
            self.state = State.succeeded

    @abstractmethod
    def _run(self):
        """What this job actually does (without all the management)."""
        pass


class JobManager(PipelineItem):
    """Object that can create jobs and compute depending on their results."""

    def create_jobs(self, env: Env) -> list[Job]:
        """Crates this JobManager's jobs."""
        self.result: Optional[dict[str, Any]]
        self._env = env
        if self.state == State.canceled:
            self.jobs = []
        else:
            self.state = State.running
            self._check_prerequisites()
            try:
                self.jobs = self._get_jobs()
            except PipelineItemFailure as failure:
                self._fail(failure)
                self.jobs = []
        return self.jobs

    @abstractmethod
    def _get_jobs(self) -> list[Job]:
        """Actually creates this JobManager's jobs (without management)."""
        pass

    def _job_states(self) -> tuple[State, ...]:
        """States of this manager's jobs."""
        return tuple(map(lambda j: j.state, self.jobs))

    def _jobs_with_state(self, state: State) -> list[Job]:
        """Filter this manager's jobs by state."""
        return list(filter(lambda j: j.state == state, self.jobs))

    def _update(self) -> None:
        """Override this function for manager-specific."""
        pass

    def update(self) -> str:
        """Update this manager's state according to its jobs and return status."""
        self._update()
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
        return self.state == State.running and len(
            self._jobs_with_state(State.succeeded)
            + self._jobs_with_state(State.canceled)
        ) == len(self.jobs)

    def any_failed(self) -> bool:
        """Returns whether this manager or its jobs had any failures so far."""
        return (
            self.state == State.failed or len(self._jobs_with_state(State.failed)) > 0
        )

    def failures(self) -> str:
        """Returns failures of failed jobs or manager itself."""
        failed = self._jobs_with_state(State.failed)
        if len(failed):
            failed_msg = "\n".join([f'"{job.name}": {job.fail_msg}' for job in failed])
            return f"{len(failed)} jobs failed:\n{failed_msg}"
        else:
            return f"{self.name} failed:\n{self.fail_msg}"

    def finalize(self) -> str:
        """Finalizes this JobManager - Does final evaluation and returns final status."""

        if self.state == State.running:
            try:
                self._evaluate()
            except PipelineItemFailure as failure:
                self._fail(failure)
            else:
                self.state = State.succeeded
                self.result = self._compute_result()

        super().finish()
        return self._get_status()

    def _evaluate(self) -> None:
        """Decide whether jobs did run as expected and return result."""
        pass

    def _compute_result(self) -> dict[str, Any]:
        """Creates result to be read by other managers."""
        return {}
