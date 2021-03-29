import os
import sys
import unittest

from ..task_config import TaskConfig
from ..solution import Solution
from .. import util


class TestCase(unittest.TestCase):
    def __init__(self, task_dir):
        super().__init__()
        self.task_dir = task_dir

    def log(self, msg, *args, **kwargs):
        print(msg, file=sys.stderr, *args, **kwargs)
        sys.stderr.flush()


class SolutionTestCase(TestCase):
    def __init__(self, task_dir, solution_name):
        super().__init__(task_dir)
        self.task_dir = task_dir
        self.solution = Solution(task_dir, solution_name)


class GeneratorTestCase(TestCase):
    def __init__(self, task_dir, data_dir, generator):
        super().__init__(task_dir)
        self.task_dir = task_dir
        self.data_dir = data_dir
        self.generator = generator


# Non-abstract test-cases common to multiple contest types.


def assertFileExists(self, path):
    self.assertTrue(
        os.path.isfile(os.path.join(self.task_dir, path)),
        f"Ve složce úlohy musí existovat soubor '{path}'",
    )


# Assumes that the file already exists!
def assertFileNotEmpty(self, path):
    self.assertTrue(
        os.path.getsize(os.path.join(self.task_dir, path)) > 0,
        f"Ve složce úlohy musí být neprázdný soubor '{path}'",
    )


class ConfigIsValid(TestCase):
    def runTest(self):
        assertFileExists(self, "config")
        TaskConfig(self.task_dir)

    def __str__(self):
        return f"Konfigurace (config) je platná"


class SampleExists(TestCase):
    def runTest(self):
        samples = util.get_samples(self.task_dir)
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
