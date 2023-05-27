from pisek.tests.task_jobs import SampleManager
from pisek.tests.job_pipeline import JobPipeline

class KasiopeaPipeline(JobPipeline):
    def __init__(self):
        self.pipeline = [
            SampleManager()
        ]
