# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2024        Antonín Maloň  <git@tonyl.eu>
# Copyright (c)   2024        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Any, NoReturn, Optional

from pisek.utils.text import tab
from pisek.env.env import Env
from pisek.config.config_types import ProgramType
from pisek.utils.paths import TaskPath, InputPath, LogPath
from pisek.task_jobs.program import ProgramsJob, RunResultKind
from pisek.task_jobs.data.testcase_info import TestcaseInfo

from .base_classes import GeneratorListInputs, GenerateInput, GeneratorTestDeterminism


class PisekV1ListInputs(GeneratorListInputs):
    """Lists all inputs for pisek-v1 generator."""

    def __init__(self, env: Env, generator: TaskPath, **kwargs) -> None:
        super().__init__(env=env, generator=generator, **kwargs)

    def _run(self) -> list[TestcaseInfo]:
        testcase_infos = []
        input_names: set[str] = set()
        self._create_inputs_list()
        for i, line in enumerate(self._get_input_lines()):
            testcase_info = self._get_testcase_info_from_line(line, i)
            if testcase_info.name in input_names:
                self._line_invalid(
                    i, line, f"Input '{testcase_info.name}' already listed"
                )
            input_names.add(testcase_info.name)
            testcase_infos.append(testcase_info)
        return testcase_infos

    def _get_testcase_info_from_line(self, line: str, line_index: int) -> TestcaseInfo:
        line = line.rstrip("\n")
        if not line:
            self._line_invalid(line_index, line, "Line empty")

        args = line.split(" ")
        input_name = args[0]
        info_args: dict[str, Any] = {}

        for arg in args[1:]:
            if "=" not in arg:
                self._line_invalid(line_index, line, "Missing '='")
            parts = arg.split("=")
            if len(parts) != 2:
                self._line_invalid(line_index, line, "Too many '='")
            arg_name, arg_value = parts
            if arg_name in info_args:
                self._line_invalid(line_index, line, f"Repeated key '{arg_name}'")
            elif arg_name == "repeat":
                try:
                    repeat_times = int(arg_value)
                    assert repeat_times > 0
                except (ValueError, AssertionError):
                    self._line_invalid(
                        line_index, line, "'repeat' should be a positive number"
                    )

                info_args[arg_name] = repeat_times
            elif arg_name == "seeded":
                if arg_value not in ("true", "false"):
                    self._line_invalid(
                        line_index, line, "'seeded' should be 'true' or 'false'"
                    )
                info_args[arg_name] = arg_value == "true"
            else:
                self._line_invalid(line_index, line, f"Unknown argument: '{arg_name}'")

        if not info_args.get("seeded", True) and info_args.get("repeat", 1) > 1:
            self._line_invalid(
                line_index, line, "For unseeded input 'repeat' must be '1'"
            )

        return TestcaseInfo.generated(input_name, **info_args)

    def _line_invalid(self, line_index: int, contents: str, reason: str) -> NoReturn:
        contents = contents.rstrip("\n")
        message = (
            f"Inputs list invalid (line {line_index+1}) - {reason}:\n"
            f"{tab(self._colored(contents, 'yellow'))}\n"
            f"Generator:"
        )
        raise self._create_program_failure(
            message, self._run_result, status=False, stderr=False
        )

    def _create_inputs_list(self) -> None:
        self._run_result = self._run_program(
            ProgramType.in_gen,
            self.generator,
            stdout=self._get_inputs_list_path(),
            stderr=LogPath.generator_log(self.generator.name),
        )
        if self._run_result.kind != RunResultKind.OK:
            raise self._create_program_failure(
                f"{self.generator} failed to list inputs",
                self._run_result,
            )

    def _get_input_lines(self) -> list[str]:
        with self._open_file(self._get_inputs_list_path()) as f:
            return f.readlines()

    def _get_inputs_list_path(self):
        return TaskPath.data_path(self._env, "inputs_list")


class PisekV1GeneratorJob(ProgramsJob):
    """Abstract class for jobs with OnlineGenerator."""

    generator: TaskPath
    seed: Optional[int]
    testcase_info: TestcaseInfo
    input_path: InputPath

    def __init__(self, env: Env, *, name: str = "", **kwargs) -> None:
        super().__init__(env=env, name=name, **kwargs)

    def _gen(self) -> None:
        args = [self.testcase_info.name]

        if self.testcase_info.seeded:
            assert self.seed is not None
            if self.seed < 0:
                raise ValueError(f"seed {self.seed} is negative")
            args.append(f"{self.seed:x}")

        result = self._run_program(
            ProgramType.in_gen,
            self.generator,
            args=args,
            stdout=self.input_path,
            stderr=self.input_path.to_log(self.generator.name),
        )
        if result.kind != RunResultKind.OK:
            raise self._create_program_failure(
                f"{self.generator} failed on input {self.testcase_info.name}, seed {self.seed:x}:",
                result,
            )


class PisekV1Generate(PisekV1GeneratorJob, GenerateInput):
    """Generates input with given name."""

    pass


class PisekV1TestDeterminism(PisekV1GeneratorJob, GeneratorTestDeterminism):
    """Tests determinism of generating a given input."""

    pass
