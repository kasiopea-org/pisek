import os
import sys
import unittest

from ..task_config import TaskConfig
from ..solution import Solution
from .. import util


class TestCase(unittest.TestCase):
    def __init__(self, task_config: TaskConfig):
        super().__init__()
        self.task_config = task_config

    def log(self, msg, *args, **kwargs):
        print(msg, file=sys.stderr, *args, **kwargs)
        sys.stderr.flush()

    def assertFileExists(self, path):
        self.assertTrue(
            os.path.isfile(os.path.join(self.task_config.task_dir, path)),
            f"Ve složce úlohy musí existovat soubor '{path}'",
        )

    def assertFileNotEmpty(self, path):
        # Assumes that the file already exists!
        self.assertTrue(
            os.path.getsize(os.path.join(self.task_config.task_dir, path)) > 0,
            f"Ve složce úlohy musí být neprázdný soubor '{path}'",
        )


class SolutionTestCase(TestCase):
    def __init__(self, task_config: TaskConfig, solution_name):
        super().__init__(task_config)
        self.solution = Solution(task_config.task_dir, solution_name)


class GeneratorTestCase(TestCase):
    def __init__(self, task_config: TaskConfig, generator):
        super().__init__(task_config)
        self.generator = generator


# Non-abstract test-cases common to multiple contest types.


class SampleExists(TestCase):
    def runTest(self):
        samples = util.get_samples(self.task_config.get_samples_dir())
        self.assertGreater(
            len(samples),
            0,
            "Ve složce s úlohou nejsou žádné samply "
            "(soubory tvaru sample*.in s odpovídajícím sample*.out)",
        )
        for sample_in, sample_out in samples:
            self.assertTrue(
                os.path.isfile(sample_in),
                f"Vzorový vstup neexistuje nebo není soubor: {sample_in}",
            )
            self.assertTrue(
                os.path.isfile(sample_out),
                f"Vzorový výstup neexistuje nebo není soubor: {sample_out}",
            )
