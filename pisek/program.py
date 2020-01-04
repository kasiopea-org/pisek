import os

from . import run
from . import util
from . import compile


class Program:
    def __init__(self, task_dir, name):
        self.task_dir = task_dir
        self.name = name
        self.executable = None

    def compile(self):
        filename = util.resolve_extension(self.task_dir, self.name)
        if filename is None:
            raise RuntimeError(
                f"Řešení {self.name} ve složce {self.task_dir} neexistuje"
            )
        self.executable = compile.compile(os.path.join(self.task_dir, filename))
        if self.executable is None:
            raise RuntimeError(f"Řešení {self.name} se nepodařilo zkompilovat")

    def compile_if_needed(self):
        # TODO: we could avoid recompiling if the binary exists and is fresh
        if not self.executable:
            self.compile()

    def run(self):
        self.compile_if_needed()
        return run.run_direct(self.executable)
