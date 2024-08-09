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

from typing import Any, NoReturn

from pisek.utils.text import tab
from pisek.utils.terminal import colored_env
from pisek.env.env import Env
from pisek.config.config_types import ProgramType
from pisek.utils.paths import TaskPath
from pisek.task_jobs.program import ProgramsJob, RunResult, RunResultKind

from .input_info import InputInfo
from .base_classes import GeneratorListInputs, GenerateInput, GeneratorTestDeterminism


class PisekGenV1ListInputs(GeneratorListInputs):
    """Lists all inputs for pisek-gen-v1 generator."""

    def __init__(self, env: Env, generator: TaskPath, **kwargs) -> None:
        super().__init__(env=env, generator=generator, **kwargs)

    def _run(self) -> list[InputInfo]:
        input_infos = []
        self._create_inputs_list()
        for i, line in enumerate(self._get_input_lines()):
            input_infos.append(self._get_input_info_from_line(line, i))
        return input_infos

    def _get_input_info_from_line(self, line: str, line_number: int) -> InputInfo:
        line = line.rstrip("\n")
        if not line:
            self._line_invalid(line_number, line, "Line empty")

        args = line.split(" ")
        input_name = args[0]
        info_args: dict[str, Any] = {}

        for arg in args[1:]:
            if "=" not in arg:
                self._line_invalid(line_number, line, "Missing '='")
            parts = arg.split("=")
            if len(parts) != 2:
                self._line_invalid(line_number, line, "Too many '='")
            arg_name, arg_value = parts
            if arg_name in info_args:
                self._line_invalid(line_number, line, f"Repeated key '{arg_name}'")
            elif arg_name == "repeat":
                if not arg_value.isnumeric() or int(arg_value) == 0:
                    self._line_invalid(
                        line_number, line, "'repeat' should be a positive number"
                    )
                info_args[arg_name] = int(arg_value)
            elif arg_name == "seeded":
                if arg_value not in ("true", "false"):
                    self._line_invalid(
                        line_number, line, "'seeded' should be 'true' or 'false'"
                    )
                info_args[arg_name] = arg_value == "true"
            else:
                self._line_invalid(line_number, line, f"Unknown argument: '{arg_name}'")

        if not info_args.get("seeded", True) and info_args.get("repeat", 1) > 1:
            self._line_invalid(
                line_number, line, "For unseeded input 'repeat' must be '1'"
            )

        return InputInfo.generated(input_name, **info_args)

    def _line_invalid(self, line_index: int, contents: str, reason: str) -> NoReturn:
        message = (
            f"Inputs list invalid (line {line_index}) - {reason}:\n"
            f"{tab(colored_env(contents, "yellow", self._env))}\n"
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
            stderr=TaskPath.log_file(self._env, "inputs_list", self.generator.name),
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


class PisekGenV1GeneratorJob(ProgramsJob):
    """Abstract class for jobs with OnlineGenerator."""

    generator: TaskPath
    seed: int
    input_info: InputInfo
    input_path: TaskPath

    def __init__(self, env: Env, *, name: str = "", **kwargs) -> None:
        super().__init__(env=env, name=name, **kwargs)

    def _gen(self) -> None:
        if self.seed < 0:
            raise ValueError(f"seed {self.seed} is negative")

        args = [self.input_info.name]
        if self.input_info.seeded:
            args.append(f"{self.seed:x}")

        result = self._run_program(
            ProgramType.in_gen,
            self.generator,
            args=args,
            stdout=self.input_path,
            stderr=TaskPath.log_file(
                self._env, self.input_path.name, self.generator.name
            ),
        )
        if result.kind != RunResultKind.OK:
            raise self._create_program_failure(
                f"{self.generator} failed on input {self.input_info.name}, seed {self.seed:x}:",
                result,
            )


class PisekGenV1Generate(PisekGenV1GeneratorJob, GenerateInput):
    """Generates input with given name."""

    pass


class PisekGenV1TestDeterminism(PisekGenV1GeneratorJob, GeneratorTestDeterminism):
    """Tests determinism of generating a given input."""

    pass
