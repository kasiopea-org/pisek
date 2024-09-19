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
from pisek.task_jobs.generator.input_info import InputInfo
from pisek.task_jobs.checker import CheckerJob

from .data import LinkInput, LinkOutput

TEST_SEED = 25265
SHORTEN_INPUTS_CUTOFF = 3


class DataManager(TaskJobManager):
    """Moves data to correct folders."""

    def __init__(self) -> None:
        super().__init__("Processing data")

    def _get_jobs(self) -> list[Job]:
        static_inputs = self.globs_to_files(
            self._env.config.input_globs, TaskPath.static_path(self._env, ".")
        )

        if self._env.config.task_type == TaskType.communication:
            static_outputs = []
        else:
            static_outputs = [path.replace_suffix(".out") for path in static_inputs]
            for static_inp, static_out in zip(static_inputs, static_outputs):
                if not static_out.exists():
                    raise PipelineItemFailure(
                        f"Missing matching output '{static_out:p}' for static input '{static_inp:p}'."
                    )

        all_static_inputs = self.globs_to_files(
            ["*.in"], TaskPath.static_path(self._env, ".")
        )
        all_input_infos: list[InputInfo] = [
            InputInfo.static(inp.name.removesuffix(".in")) for inp in all_static_inputs
        ] + self.prerequisites_results[GENERATOR_MAN_CODE]["inputs"]
        all_input_infos.sort(key=lambda info: info.name)

        # put inputs in subtasks
        self._input_infos: dict[int, list[InputInfo]] = {}
        for num, sub in self._env.config.subtasks.items():
            self._input_infos[sub.num] = []
            for input_info in all_input_infos:
                if sub.in_subtask(input_info.task_path(self._env, TEST_SEED).name):
                    self._input_infos[sub.num].append(input_info)
            if len(self._input_infos[sub.num]) == 0:
                raise PipelineItemFailure(
                    f"No inputs for subtask {num} with globs {sub.all_globs}."
                )

        used_inputs = set(sum(self._input_infos.values(), start=[]))
        self._report_not_included_inputs(
            used_inputs - set(self._input_infos[self._env.config.subtasks_count - 1])
        )
        self._report_unused_inputs(set(all_input_infos) - used_inputs)

        jobs: list[Job] = []
        for path in static_inputs:
            jobs.append(LinkInput(self._env, path))

        for path in static_outputs:
            jobs.append(LinkOutput(self._env, path))

        for subtask, inputs in self._input_infos.items():
            for inp in inputs:
                if inp.is_generated:
                    continue

                if subtask > 0 and self._env.config.checker is not None:
                    jobs.append(
                        CheckerJob(
                            self._env,
                            self._env.config.checker,
                            TaskPath.static_path(
                                self._env, inp.task_path(self._env).name
                            ),
                            subtask,
                        )
                    )

        return jobs

    def _report_unused_inputs(self, unused_inputs: Iterable[InputInfo]) -> None:
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
                        f"Unused {'generated' if inp.is_generated else 'static'} input: '{inp.name}.in'"
                    )

    def _report_not_included_inputs(
        self, not_included_inputs: Iterable[InputInfo]
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

    def _short_inputs_list(self, inputs: Iterable[InputInfo]) -> str:
        return self._short_list(
            list(map(lambda inp: f"{inp.name}.in", inputs)), SHORTEN_INPUTS_CUTOFF
        )

    def _compute_result(self) -> dict[str, Any]:
        res = {"input_info": self._input_infos}
        return res
