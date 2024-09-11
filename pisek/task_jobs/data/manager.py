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

import re
from typing import Any

from pisek.utils.paths import TaskPath
from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.config.config_types import TaskType, DataFormat
from pisek.task_jobs.task_manager import TaskJobManager, GENERATOR_MAN_CODE
from pisek.task_jobs.generator.input_info import InputInfo
from pisek.task_jobs.tools import IsClean
from pisek.task_jobs.checker import CheckerJob

from .data import LinkInput, LinkOutput, InputSmall, OutputSmall

TEST_SEED = 25265


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
        unused_inputs = list(
            sorted(set(all_input_infos) - used_inputs, key=lambda inp: inp.name)
        )
        if self._env.config.checks.no_unused_inputs and len(unused_inputs):
            if self._env.verbosity <= 0:
                CUTOFF = 3
                unused_inputs_text = ", ".join(
                    map(lambda inp: f"{inp.name}.in", unused_inputs[:CUTOFF])
                )
                if len(unused_inputs) > CUTOFF:
                    unused_inputs_text += ",…"
                self._warn(
                    f"{len(unused_inputs)} unused input{'s' if len(unused_inputs) >= 2 else ''}. "
                    f"({unused_inputs_text})"
                )
            else:
                for inp in unused_inputs:
                    self._warn(
                        f"Unused {'generated' if inp.is_generated else 'static'} input: '{inp.name}.in'"
                    )

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

    def _compute_result(self) -> dict[str, Any]:
        res = {"input_info": self._input_infos}
        return res
