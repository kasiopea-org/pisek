from typing import List

from pisek.jobs.jobs import Job, JobManager
from pisek.jobs.job_pipeline import JobPipeline

from pisek.jobs.parts.samples import SampleManager
from pisek.jobs.parts.generator import GeneratorManager
from pisek.jobs.parts.checker import CheckerManager
from pisek.jobs.parts.judge import JudgeManager
from pisek.jobs.parts.solution import SolutionManager

import os
from pisek.task_config import TaskConfig
from pisek.env import Env
from pisek.jobs.cache import Cache

class KasiopeaPipeline(JobPipeline):
    def __init__(self, env):
        super().__init__(env)
        self.pipeline = [
            samples := SampleManager(),
            generator := GeneratorManager(),
            checker := CheckerManager(),
            judge := JudgeManager(),
            primary_solution := SolutionManager(env.config.primary_solution)
        ]
        checker.add_prerequisite(samples)
        checker.add_prerequisite(generator)
        
        primary_solution.add_prerequisite(generator)
        primary_solution.add_prerequisite(judge)

        for solution in env.config.solutions:
            if solution == env.config.primary_solution:
                continue
            self.pipeline.append(solution := SolutionManager(solution))
            solution.add_prerequisite(primary_solution)
        

path = "./fixtures/guess"
if os.path.exists(path + "/.pisek_cache"):
    os.remove(path + "/.pisek_cache")
env = Env(
    task_dir=path,
    inputs=5,
    strict=False,
    no_checker=False,
    full=True,
    config=TaskConfig(path)
)
p = KasiopeaPipeline(env.fork())
p.run_jobs(Cache(env), env)
