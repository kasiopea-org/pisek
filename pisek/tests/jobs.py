from abc import ABC, abstractmethod
import hashlib

class Job(ABC):
    def __init__(self, name, required_files, env):
        self.name = name
        self._required_files = required_files
        self._env = env

    _required_envs = []
    def access_env(self, name):
        if name not in self._required_envs:
            raise ValueError(f"Variable '{name}' is not reserved in required_envs.")
        return self._env.get(name)

    def signature(self):
        sign = hashlib.sha256(self.name.encode())
        for variable in self._required_envs:
            sign.update(f"{variable}={self.access_env(variable)}\n".encode())
        for file in self._required_files:
            with open(file) as f:
                file_sign = hashlib.file_digest(f, "sha256")
            sign.update(f"{file}={file_sign}\n".encode())
        return (self.name, sign)

    def run_job(self, cache):
        job_name, sign = self.signature()
        if cache.job_exists(job_name) and cache.get_sign(job_name) != sign:
            cache.add(self.run())
        return cache.get_result(job_name)

    @abstractmethod
    def run(self):
        pass

class JobManager(ABC):
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def create_jobs(self):
        pass

    @abstractmethod
    def status(self):
        pass
