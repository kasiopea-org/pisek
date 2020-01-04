import os

from . import program


class Solution(program.Program):
    def run_on_file(self, input_file):
        """ Runs the solution and stores the output in a reasonably named file in data/ """
        data_dir = os.path.join(self.task_dir, "data/")
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        output_filename = "{}.{}.out".format(
            os.path.splitext(os.path.basename(input_file))[0], self.name
        )
        output_file = os.path.join(data_dir, output_filename)

        self.compile_if_needed()

        # self.assertTrue(f"Chyba při spuštění {self.name} na {input_file}",)
        ok = program.run(self.executable, input_file, output_file)
        return output_file if ok else None
