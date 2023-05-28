from pisek.tests.task_jobs import SampleManager
from pisek.tests.job_pipeline import JobPipeline

from pisek.task_config import TaskConfig
from pisek.env import Env
from pisek.tests.cache import Cache

class KasiopeaPipeline(JobPipeline):
    def __init__(self):
        self.pipeline = [
            SampleManager()
        ]


p = KasiopeaPipeline()
path = "./fixtures/soucet_kasiopea"
env = Env(
    task_dir=path,
    config=TaskConfig(path)
)
p.run_jobs(Cache(env), env)
