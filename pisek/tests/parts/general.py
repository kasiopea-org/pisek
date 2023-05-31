from pisek.env import Env
from pisek.tests.jobs import State, Job, JobManager
from pisek.tests.parts.task_job import TaskJob

from pisek.program import Program

class Compile(TaskJob):
    def __init__(self, program: Program, env: Env) -> None:
        self.program = program
        super().__init__(        
            name=f"Compile {program.name}",
            env=env
        )
    
    def _run(self):
        self.program.compile()
