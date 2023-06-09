from typing import List

from pisek.tests.jobs import Job, JobManager
from pisek.tests.job_pipeline import JobPipeline

from pisek.tests.parts.samples import SampleManager
from pisek.tests.parts.generator import OnlineGeneratorManager
from pisek.tests.parts.checker import CheckerManager

from pisek.task_config import TaskConfig
from pisek.env import Env
from pisek.tests.cache import Cache

class KasiopeaPipeline(JobPipeline):
    def __init__(self):
        self.pipeline = [
            SampleManager(),
            OnlineGeneratorManager(),
            CheckerManager()
        ]


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
