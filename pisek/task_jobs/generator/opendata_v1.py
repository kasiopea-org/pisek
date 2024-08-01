from pisek.env.env import Env
from pisek.jobs.jobs import PipelineItemFailure
from pisek.config.config_types import ProgramType
from pisek.utils.paths import TaskPath
from pisek.task_jobs.program import ProgramsJob, RunResult, RunResultKind

from .input_info import InputInfo
from .base_classes import GeneratorListInputs, GenerateInput


class OpendataV1ListInputs(GeneratorListInputs):
    """Lists all inputs for opendata-v1 gen - one for each subtask."""

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

    def _gen(self) -> RunResult:
        if self.seed < 0:
            raise PipelineItemFailure(f"Seed {self.seed} is negative.")

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
                f"{self.generator} failed on subtask {subtask}, seed {self.seed:x}:", result
            )

        return result


class OpendataV1Generate(GenerateInput, OpendataV1GeneratorJob):
    """Generates single input using OnlineGenerator."""
    pass


class OnlineGeneratorDeterministic(OpendataV1GeneratorJob):
    """Test whether generating given input again has same result."""

    def __init__(
        self,
        env: Env,
        generator: TaskPath,
        input_: TaskPath,
        subtask: int,
        seed: int,
        **kwargs,
    ) -> None:
        super().__init__(
            env=env,
            name=f"Generator is deterministic (name {subtask}, seed {seed:x})",
            generator=generator,
            input_=input_,
            subtask=subtask,
            seed=seed,
            **kwargs,
        )

    def _run(self) -> None:
        copy_file = self.input_.replace_suffix(".in2")
        self._gen(copy_file, self.seed, self.subtask)
        if not self._files_equal(self.input_, copy_file):
            raise PipelineItemFailure(
                f"Generator is not deterministic. Files {self.input_:p} and {copy_file:p} differ "
                f"(subtask {self.subtask}, seed {self.seed})",
            )
