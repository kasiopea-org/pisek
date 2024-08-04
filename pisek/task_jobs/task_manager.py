# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from pisek.utils.paths import TaskPath
from pisek.config.task_config import SubtaskConfig
from pisek.jobs.status import StatusJobManager
from pisek.task_jobs.task_job import TaskHelper
from pisek.task_jobs.generator.input_info import InputInfo


TOOLS_MAN_CODE = "tools"
GENERATOR_MAN_CODE = "generator"
INPUTS_MAN_CODE = "inputs"
CHECKER_MAN_CODE = "checker"
JUDGE_MAN_CODE = "judge"
SOLUTION_MAN_CODE = "solution_"
DATA_MAN_CODE = "data"


class TaskJobManager(StatusJobManager, TaskHelper):
    """JobManager class that implements useful methods"""

    def _get_static_samples(self) -> list[tuple[TaskPath, TaskPath]]:
        """Returns the list [(sample1.in, sample1.out), …]."""
        ins = filter(
            lambda inp: not inp.is_generated,
            self._subtask_inputs(self._env.config.subtasks[0]),
        )
        return [
            (inp.task_path(self._env), TaskPath.output_static_file(self._env, inp.name))
            for inp in ins
        ]

    def _subtask_inputs(self, subtask: SubtaskConfig) -> list[InputInfo]:
        """Get all inputs of given subtask."""
        return self.prerequisites_results[INPUTS_MAN_CODE]["input_info"][subtask.num]

    def _all_inputs(self) -> dict[int, list[InputInfo]]:
        """Get all inputs grouped by subtask."""
        return self.prerequisites_results[INPUTS_MAN_CODE]["input_info"]
