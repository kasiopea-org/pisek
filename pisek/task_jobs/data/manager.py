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

from typing import Any, Iterable

from pisek.utils.paths import TaskPath
from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.config.config_types import TaskType
from pisek.task_jobs.task_manager import TaskJobManager, GENERATOR_MAN_CODE
from pisek.task_jobs.data.testcase_info import TestcaseInfo, TestcaseGenerationMode
from pisek.task_jobs.checker import CheckerJob

from .data import LinkInput, LinkOutput

TEST_SEED = 25265
SHORTEN_INPUTS_CUTOFF = 3


class DataManager(TaskJobManager):
    """Moves data to correct folders."""

    def __init__(self) -> None:
        super().__init__("Processing data")

    def _get_jobs(self) -> list[Job]:
        sample_inputs = self.globs_to_files(
            self._env.config.subtasks[0].all_globs, TaskPath.static_path(self._env, ".")
        )
        static_inputs = self.globs_to_files(
            self._env.config.input_globs, TaskPath.static_path(self._env, ".")
        )

        static_outputs: list[TaskPath] = []
        if self._env.config.task_type != TaskType.communication:
            for static_inp in static_inputs:
                static_out = static_inp.replace_suffix(".out")
                if static_out.exists():
                    static_outputs.append(static_out)
                elif static_inp in sample_inputs:
                    raise PipelineItemFailure(
                        f"Missing matching output '{static_out:p}' for sample input '{static_inp:p}'."
                    )

        all_static_inputs = self.globs_to_files(
            ["*.in"], TaskPath.static_path(self._env, ".")
        )
        all_testcase_infos: list[TestcaseInfo] = [
            (
                TestcaseInfo.static(inp.name.removesuffix(".in"))
                if self._env.config.task_type == TaskType.communication
                or inp.replace_suffix(".out").exists()
                else TestcaseInfo.mixed(inp.name.removesuffix(".in"))
            )
            for inp in all_static_inputs
        ] + self.prerequisites_results[GENERATOR_MAN_CODE]["inputs"]

        all_testcase_infos.sort(key=lambda info: info.name)

        # put inputs in subtasks
        self._testcase_infos: dict[int, list[TestcaseInfo]] = {}
        for num, sub in self._env.config.subtasks.items():
            self._testcase_infos[sub.num] = []
            for testcase_info in all_testcase_infos:
                inp_path = testcase_info.input_path(self._env, TEST_SEED).name
                if sub.in_subtask(inp_path):
                    if (
                        num == 0
                        and testcase_info.generation_mode
                        != TestcaseGenerationMode.static
                    ):
                        raise PipelineItemFailure(
                            f"Sample inputs must be static, but '{inp_path}' is {testcase_info.generation_mode}."
                        )
                    self._testcase_infos[sub.num].append(testcase_info)
            if len(self._testcase_infos[sub.num]) == 0:
                raise PipelineItemFailure(
                    f"No inputs for subtask {num} with globs {sub.all_globs}."
                )

        used_inputs = set(sum(self._testcase_infos.values(), start=[]))
        self._report_not_included_inputs(
            used_inputs - set(self._testcase_infos[self._env.config.subtasks_count - 1])
        )
        self._report_unused_inputs(set(all_testcase_infos) - used_inputs)

        jobs: list[Job] = []
        for path in static_inputs:
            jobs.append(LinkInput(self._env, path))

        for path in static_outputs:
            jobs.append(LinkOutput(self._env, path))

        for subtask, testcases in self._testcase_infos.items():
            for testcase in testcases:
                if testcase.generation_mode == TestcaseGenerationMode.generated:
                    continue

                if subtask > 0 and self._env.config.checker is not None:
                    jobs.append(
                        CheckerJob(
                            self._env,
                            self._env.config.checker,
                            TaskPath.static_path(
                                self._env, testcase.input_path(self._env).name
                            ),
                            subtask,
                        )
                    )

        return jobs

    def _report_unused_inputs(self, unused_inputs: Iterable[TestcaseInfo]) -> None:
        inputs = list(sorted(unused_inputs, key=lambda inp: inp.name))
        if self._env.config.checks.no_unused_inputs and inputs:
            if self._env.verbosity <= 0:
                self._warn(
                    f"{len(inputs)} unused input{'s' if len(inputs) >= 2 else ''}. "
                    f"({self._short_inputs_list(inputs)})"
                )
            else:
                for inp in inputs:
                    self._warn(
                        f"Unused {'generated' if inp.generation_mode == TestcaseGenerationMode.generated else 'static'} input: '{inp.name}.in'"
                    )

    def _report_not_included_inputs(
        self, not_included_inputs: Iterable[TestcaseInfo]
    ) -> None:
        inputs = list(sorted(not_included_inputs, key=lambda inp: inp.name))
        if self._env.config.checks.all_inputs_in_last_subtask and inputs:
            if self._env.verbosity <= 0:
                self._warn(
                    f"{len(inputs)} input{'s' if len(inputs) >= 2 else ''} "
                    "not included in last subtask. "
                    f"({self._short_inputs_list(inputs)})"
                )
            else:
                for inp in inputs:
                    self._warn(f"Input '{inp.name}.in' not included in last subtask.")

    def _short_inputs_list(self, inputs: Iterable[TestcaseInfo]) -> str:
        return self._short_list(
            list(map(lambda inp: f"{inp.name}.in", inputs)), SHORTEN_INPUTS_CUTOFF
        )

    def _compute_result(self) -> dict[str, Any]:
        res = {"testcase_info": self._testcase_infos}
        return res
