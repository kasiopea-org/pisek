from abc import ABC, abstractmethod
import hashlib
from enum import Enum
from typing import Any

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

    def check_prerequisites(self):
        if self.prerequisites > 0:
            raise RuntimeError(f"{self.__class__.__name__} {self.name} prerequisites not finished ({self.prerequisites} remaining).")
    
    def add_prerequisite(self, item):
        self.prerequisites += 1
        item.required_by.append(self)

    def finish(self):
        for item in self.required_by:
            item.prerequisites -= 1


class Job(PipelineItem):
    def __init__(self, name : str, required_files : list[str], env) -> None:
        self._required_files = required_files
        self._env = env
        self.result = None
        super().__init__(name)

    _required_envs = []
    def _access_env(self, name : str) -> Any:
        if name not in self._required_envs:
            raise ValueError(f"Variable '{name}' is not reserved in required_envs.")
        return self._env.get(name)

    def signature(self) -> str:
        sign = hashlib.sha256()
        for variable in self._required_envs:
            sign.update(f"{variable}={self._access_env(variable)}\n".encode())
        for file in self._required_files:
            with open(file) as f:
                file_sign = hashlib.file_digest(f, "sha256")
            sign.update(f"{file_sign}\n".encode())
        return sign

    def run_job(self, cache):
        if self.state == State.canceled:
            return None
        self.check_prerequisites()
        self.state = State.running
        sign = self.signature()
        if sign not in cache:
            cache[sign] = self._run()
        self.result = cache[sign]
        self.state = State.succeeded
        return cache[sign]

    @abstractmethod
    def _run(self):
        pass


class JobManager(PipelineItem):
    def create_jobs(self, env) -> list[Job]:
        self.check_prerequisites()
        self.jobs = self._get_jobs()
        self.expectations = []
        return self.jobs

    def expect_all(self, jobs, state : State, result : Any):
        self.expect(all, jobs, state, result)

    def expect_any(self, jobs, state : State, result : Any):
        self.expect(any, jobs, state, result)

    def expect(self, what : callable[[list[bool]], bool], jobs : list[Job], state : State, result : Any) -> callable[[], bool]:
        def f():
            return what(map(
                lambda j: j.state == state and (result is None or j.result == result),
                jobs
            ))
        self.expectations.append(f)

    @abstractmethod
    def _get_jobs(self) -> list[Job]:
        pass

    def update(self):
        new_state = State.succeeded
        for job in self.jobs:
            if job.state == State.in_queue or job.state == State.running:
                new_state = State.in_queue
            elif job.state == State.failed:
                new_state = State.failed
        self.state = new_state
        if self.state == State.failed:
            self.cancel_jobs()

        return self._get_status()

    def cancel_jobs(self) -> None:
        for job in self.jobs:
            if job.state == State.in_queue:
                job.state = State.canceled

    @abstractmethod
    def _get_status(self) -> str:
        return ""

    def finish(self) -> str:
        super().finish()
        return self._get_status()
