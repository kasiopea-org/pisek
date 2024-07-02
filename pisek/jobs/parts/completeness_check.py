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
from pisek.config.config_types import JudgeType
from pisek.jobs.jobs import Job
from pisek.jobs.parts.task_job import TaskJobManager, SOLUTION_MAN_CODE


class CompletenessCheck(TaskJobManager):
    """Checks task as a whole."""

    def __init__(self):
        super().__init__("Completeness check")

    def _get_jobs(self) -> list[Job]:
        return []

    def _get_judge_outs(self) -> set[TaskPath]:
        judge_outs = set()
        for solution in self._env.solutions:
            judge_outs |= self.prerequisites_results[f"{SOLUTION_MAN_CODE}{solution}"][
                "judge_outs"
            ]
        return judge_outs

    def _check_solution_succeeds_only_on(
        self, sol_name: str, subtasks: list[int]
    ) -> bool:
        subtasks_res = self.prerequisites_results[f"{SOLUTION_MAN_CODE}{sol_name}"][
            "subtasks"
        ]
        for num in self._env.config.subtasks:
            if num == 0:
                continue  # Skip samples
            if (subtasks_res[num] == 1.0) != (num in subtasks):
                return False
        return True

    def _check_dedicated_solutions(self) -> None:
        """Checks that each subtask has it's own dedicated solution."""
        if self._env.config.checks.solution_for_each_subtask:
            for num, subtask in self._env.config.subtasks.items():
                if num == 0:
                    continue  # Samples

                ok = False
                for solution in self._env.solutions:
                    if self._check_solution_succeeds_only_on(
                        solution, [num] + subtask.all_predecessors
                    ):
                        ok = True
                        break

                if not ok:
                    self._warn(f"{subtask.name} has no dedicated solution")

    def _check_cms_judge(self) -> None:
        """Checks that cms judge's stdout & stderr contains only one line."""
        if self._env.config.judge_type == JudgeType.cms:
            for judge_out in self._get_judge_outs():
                with open(judge_out.path) as f:
                    lines = f.read().rstrip().split("\n")
                if len(lines) > 1:
                    self._warn(f"{judge_out:p} contains multiple lines")
                    if self._env.verbosity <= 0:
                        return

    def _evaluate(self) -> None:
        self._check_dedicated_solutions()
        self._check_cms_judge()
