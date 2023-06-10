from typing import List

from pisek.jobs.jobs import Job, JobManager
from pisek.jobs.job_pipeline import JobPipeline

from pisek.jobs.parts.samples import SampleManager
from pisek.jobs.parts.generator import OnlineGeneratorManager
from pisek.jobs.parts.checker import CheckerManager

from pisek.task_config import TaskConfig
from pisek.env import Env
from pisek.jobs.cache import Cache

class KasiopeaPipeline(JobPipeline):
    def __init__(self):
        self.pipeline = [
            samples := SampleManager(),
            generator := OnlineGeneratorManager(),
            checker := CheckerManager(),
        ]
        checker.add_prerequisite(generator)


p = KasiopeaPipeline()
path = "./fixtures/soucet_kasiopea"
env = Env(
    task_dir=path,
    inputs=5,
    strict=False,
    no_checker=False,
    config=TaskConfig(path)
)
p.run_jobs(Cache(env), env)
