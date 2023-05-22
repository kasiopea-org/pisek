from abc import ABC, abstractmethod
import hashlib
from enum import Enum
from typing import Any

State = Enum('State', ['in_queue', 'running', 'finished'])
class Job(ABC):
    def __init__(self, name : str, required_files : list[str], env) -> None:
        self.name = name
        self.state = State.in_queue
        self._required_files = required_files
        self._env = env

    _required_envs = []
    def _access_env(self, name : str) -> Any:
        if name not in self._required_envs:
            raise ValueError(f"Variable '{name}' is not reserved in required_envs.")
        return self._env.get(name)

    def signature(self) -> tuple[str, str]:
        sign = hashlib.sha256(self.name.encode())
        for variable in self._required_envs:
            sign.update(f"{variable}={self._access_env(variable)}\n".encode())
        for file in self._required_files:
            with open(file) as f:
                file_sign = hashlib.file_digest(f, "sha256")
            sign.update(f"{file}={file_sign}\n".encode())
        return (self.name, sign)

    def run_job(self, cache):
        self.state = State.running
        job_name, sign = self.signature()
        if cache.job_exists(job_name) and cache.get_sign(job_name) != sign:
            cache.add(self._run())
        self.state = State.finished
        return cache.get_result(job_name)

    @abstractmethod
    def _run(self):
        pass

class JobManager(ABC):
    def __init__(self, name : str) -> None:
        self.name = name
        self.state = State.in_queue

    def create_jobs(self) -> list[Job]:
        self.state = State.running
        self.jobs = self._get_jobs()
        return self.jobs

    @abstractmethod
    def _get_jobs(self) -> list[Job]:
        pass

    def update(self):
        new_state = State.finished
        for job in self.jobs:
            if job.state != State.finished:
                new_state = State.running
                break
        self.state = new_state
        return self._get_status()

    @abstractmethod
    def _get_status(self) -> str:
        return ""
