from pisek.env.env import Env
from pisek.config.config_types import ProgramType
from pisek.utils.paths import TaskPath
from pisek.task_jobs.program import ProgramsJob, RunResult, RunResultKind

from .input_info import InputInfo
from .base_classes import GeneratorListInputs, GenerateInput, GeneratorTestDeterminism


class OpendataV1ListInputs(GeneratorListInputs):
    """Lists all inputs for opendata-v1 generator - one for each subtask."""

    def _run(self) -> list[InputInfo]:
        return [
            InputInfo.generated(f"{subtask:02}")
            for subtask in self._env.config.subtasks
            if subtask != 0
        ]


class OpendataV1GeneratorJob(ProgramsJob):
    """Abstract class for jobs with OnlineGenerator."""

    generator: TaskPath
    seed: int
    input: TaskPath

    def _gen(self) -> None:
        if self.seed < 0:
            raise ValueError(f"Seed {self.seed} is negative.")

        subtask = int(self.input.name.removesuffix(".in"))

        result = self._run_program(
            ProgramType.in_gen,
            self.generator,
            args=[str(subtask), f"{self.seed:x}"],
            stdout=self.input,
            stderr=TaskPath.log_file(self._env, self.input.name, self.generator.name),
        )
        if result.kind != RunResultKind.OK:
            raise self._create_program_failure(
                f"{self.generator} failed on subtask {subtask}, seed {self.seed:x}:",
                result,
            )


class OpendataV1Generate(OpendataV1GeneratorJob, GenerateInput):
    """Generates input with given name."""

    pass


class OpendataV1TestDeterminism(OpendataV1GeneratorJob, GeneratorTestDeterminism):
    """Tests determinism of generating a given input."""

    pass
