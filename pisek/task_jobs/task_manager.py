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

from pisek.utils.paths import TaskPath, InputPath, OutputPath
from pisek.config.task_config import SubtaskConfig
from pisek.jobs.status import StatusJobManager
from pisek.task_jobs.task_job import TaskHelper
from pisek.task_jobs.data.testcase_info import TestcaseInfo


TOOLS_MAN_CODE = "tools"
GENERATOR_MAN_CODE = "generator"
INPUTS_MAN_CODE = "inputs"
CHECKER_MAN_CODE = "checker"
JUDGE_MAN_CODE = "judge"
SOLUTION_MAN_CODE = "solution_"
DATA_MAN_CODE = "data"


class TaskJobManager(StatusJobManager, TaskHelper):
    """JobManager class that implements useful methods"""

    def _get_samples(self) -> list[tuple[InputPath, OutputPath]]:
        """Returns the list [(sample1.in, sample1.out), …]."""
        return [
            (
                inp.input_path(self._env),
                inp.reference_output(self._env),
            )
            for inp in self._subtask_testcases(self._env.config.subtasks[0])
        ]

    def _subtask_testcases(self, subtask: SubtaskConfig) -> list[TestcaseInfo]:
        """Get all inputs of given subtask."""
        return self.prerequisites_results[INPUTS_MAN_CODE]["testcase_info"][subtask.num]

    def _all_testcases(self) -> dict[int, list[TestcaseInfo]]:
        """Get all inputs grouped by subtask."""
        return self.prerequisites_results[INPUTS_MAN_CODE]["testcase_info"]
