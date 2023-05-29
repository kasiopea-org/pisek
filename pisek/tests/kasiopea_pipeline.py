from typing import List

from pisek.tests.jobs import Job, JobManager
from pisek.tests.task_jobs import SampleManager, OnlineGeneratorManager
from pisek.tests.job_pipeline import JobPipeline

from pisek.task_config import TaskConfig
from pisek.env import Env
from pisek.tests.cache import Cache

class KasiopeaPipeline(JobPipeline):
    def __init__(self):
        self.pipeline = [
            SampleManager(),
            OnlineGeneratorManager()
        ]


p = KasiopeaPipeline()
path = "./fixtures/soucet_kasiopea"
env = Env(
    task_dir=path,
    inputs=5,
    config=TaskConfig(path)
)
p.run_jobs(Cache(env), env)
