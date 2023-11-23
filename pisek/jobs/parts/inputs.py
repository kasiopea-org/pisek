# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
from typing import Any

from pisek.jobs.jobs import Job, PipelineItemFailure
from pisek.env import Env
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager, GENERATED_DIR


class InputManager(TaskJobManager):
    def __init__(self):
        self._static_inputs = []
        self._generated_inputs = []
        self._static_outputs = []
        super().__init__("Checking inputs")

    def _get_jobs(self) -> list[Job]:
        self._static_inputs = self.globs_to_files(
            self._env.config.subtasks[0].all_globs,
            self._resolve_path(self._env.config.static_subdir),
        )
        self._static_outputs = self.globs_to_files(
            map(lambda x: x.replace(".in", ".out") , self._env.config.subtasks[0].all_globs),
            self._resolve_path(self._env.config.static_subdir),
        )
        self._generated_inputs = self.globs_to_files(
            self._env.config.subtasks[0].all_globs,
            self._resolve_path(GENERATED_DIR)
        )

        self._all = self._static_inputs + self._generated_inputs + self._static_outputs
        jobs: list[Job] = []

        # TODO: Check matching sample inputs for outputs 

        for fname in self._all:
            jobs += [
                non_empty := InputNotEmpty(self._env, fname),
                copy := CopyInput(self._env, fname),
            ]
 
        # TODO: Check existence of input for each subtask 

        return jobs

    def _compute_result(self) -> dict[str, Any]:
        return {
            "inputs": self._static_inputs + self._generated_inputs,
            "outputs": self._static_outputs,
            "all": self._all,
        }


class InputJob(TaskJob):
    def __init__(self, env: Env, name: str, sample: str) -> None:
        super().__init__(env, name)
        self.input = sample


class InputNotEmpty(InputJob):
    """Check that input file is not empty."""
    pass


class CopyInput(InputJob):
    """Copy input to into data folder so we can treat them normally."""
    pass
