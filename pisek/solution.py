import os
from typing import Optional

from . import util
from . import program


class Solution(program.Program):
    def run_on_file(self, input_file: str) -> Optional[str]:
        """ Runs the solution and stores the output in a reasonably named file in data/ """
        data_dir = util.get_data_dir(self.task_dir)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        output_filename = util.get_output_name(input_file, solution_name=self.name)
        output_file = os.path.join(data_dir, output_filename)

        self.compile_if_needed()
        assert self.executable is not None

        # self.assertTrue(f"Chyba při spuštění {self.name} na {input_file}",)
        ok = program.run(self.executable, input_file, output_file)
        return output_file if ok else None
