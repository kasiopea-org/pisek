import os
import shutil

from pisek.env.env import Env
from pisek.config.config_types import ProgramType
from pisek.utils.paths import TaskPath
from pisek.task_jobs.program import RunResultKind

from .input_info import InputInfo
from .base_classes import GeneratorListInputs, GenerateInput


class CmsOldListInputs(GeneratorListInputs):
    """Lists all inputs for cms-old generator - by running it."""

    def __init__(self, env: Env, generator: TaskPath, **kwargs) -> None:
        super().__init__(env, generator, name="Run generator", **kwargs)

    def _run(self) -> list[InputInfo]:
        """Generates all inputs."""
        gen_dir = TaskPath.generated_path(self._env, ".")
        try:
            shutil.rmtree(gen_dir.path)
        except FileNotFoundError:
            pass
        self.makedirs(gen_dir, exist_ok=False)

        run_result = self._run_program(
            ProgramType.in_gen,
            self.generator,
            args=[gen_dir.path],
            stderr=TaskPath.log_file(self._env, None, self.generator.name),
        )
        self._access_file(gen_dir)

        if run_result.kind != RunResultKind.OK:
            raise self._create_program_failure("Generator failed:", run_result)

        inputs = []
        for inp in os.listdir(TaskPath.generated_path(self._env, ".").path):
            if inp.endswith(".in"):
                inputs.append(
                    InputInfo.generated(inp.removesuffix(".in"), seeded=False)
                )
        return inputs



class CmsOldGenerate(GenerateInput):
    def __init__(
        self, env: Env, generator: TaskPath, input_info: InputInfo, seed: int, **kwargs
    ) -> None:
        super().__init__(
            env, generator, input_info, seed, name=f"Serve {input_info.task_path(env).name}", **kwargs
        )

    def _gen(self):
        self._link_file(
            TaskPath.generated_path(self._env, self.input.name),
            TaskPath.input_path(self._env, self.input.name),
            overwrite=True,
        )
