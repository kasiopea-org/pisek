import os
from typing import Optional, Tuple

from . import util
from . import program


class Solution(program.Program):
    def run_on_file(
        self, input_file: str, timeout: int = util.DEFAULT_TIMEOUT
    ) -> Tuple[program.RunResult, Optional[str]]:
        """
        Runs the solution and stores the output in a reasonably named file in the same dir
        """
        data_dir = os.path.dirname(input_file)

        output_filename = util.get_output_name(input_file, solution_name=self.name)
        output_file = os.path.join(data_dir, output_filename)

        self.compile_if_needed()
        assert self.executable is not None

        res = program.run(self.executable, input_file, output_file, timeout)

        if res == program.RunResult.OK:
            return res, output_file
        else:
            return res, None
