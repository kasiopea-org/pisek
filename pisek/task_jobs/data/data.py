# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from pisek.jobs.jobs import PipelineItemFailure
from pisek.env.env import Env
from pisek.utils.paths import TaskPath
from pisek.task_jobs.task_job import TaskJob


class DataJob(TaskJob):
    def __init__(self, env: Env, name: str, data: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env,
            name=name,
            **kwargs,
        )
        self.data = data


class LinkData(DataJob):
    """Link data to into dest folder."""

    def __init__(self, env: Env, data: TaskPath, dest: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env, name=f"Link {data:p} to {dest:p}/", data=data, **kwargs
        )
        self.dest = TaskPath(dest.path, self.data.name)

    def _run(self):
        self._link_file(self.data, self.dest, overwrite=True)


class LinkInput(LinkData):
    """Copy input to its place."""

    def __init__(self, env: Env, input_: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env, data=input_, dest=TaskPath.input_path(self._env, "."), **kwargs
        )


class LinkOutput(LinkData):
    """Copy output to its place."""

    def __init__(self, env: Env, output: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env, data=output, dest=TaskPath.output_path(self._env, "."), **kwargs
        )


MB = 1024 * 1024


class InputSmall(DataJob):
    """Checks that input is small enough to download."""

    def __init__(self, env: Env, input_: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env,
            name=f"Input {input_:n} is smaller than {env.config.limits.input_max_size}MB",
            data=input_,
            **kwargs,
        )

    def _run(self):
        max_size = self._env.config.limits.input_max_size
        if (sz := self._file_size(self.data)) > max_size * MB:
            raise PipelineItemFailure(
                f"Input {self.data:p} is bigger than {max_size}MB: {(sz+MB-1)//MB}MB"
            )


class OutputSmall(DataJob):
    """Checks that output is small enough to upload."""

    def __init__(self, env: Env, output: TaskPath, **kwargs) -> None:
        super().__init__(
            env=env,
            name=f"Output {output:n} is smaller than {env.config.limits.output_max_size}MB",
            data=output,
            **kwargs,
        )

    def _run(self):
        max_size = self._env.config.limits.output_max_size
        if (sz := self._file_size(self.data)) > max_size * MB:
            raise PipelineItemFailure(
                f"Output {self.data} is bigger than {max_size}MB: {(sz+MB-1)//MB}MB"
            )
