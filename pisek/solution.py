import os

from . import run
from . import util
from . import compile


class Solution:
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

    def run_on_file(self, input_file):
        """ Runs the solution and stores the output in a reasonably named file in data/ """
        data_dir = os.path.join(self.task_dir, "data/")
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        output_filename = "{}.{}.out".format(
            os.path.splitext(os.path.basename(input_file))[0], self.name
        )
        output_file = os.path.join(data_dir, output_filename)

        # TODO: maybe we should check whether the executable is fresh, but if we are just
        # running a batch job this should not be a problem
        if not self.executable:
            self.compile()

        # self.assertTrue(f"Chyba při spuštění {self.name} na {input_file}",)
        ok = run.run(self.executable, input_file, output_file)
        return output_file if ok else None

    def run(self):
        if not self.executable:
            self.compile()

        return run.run_direct(self.executable)
