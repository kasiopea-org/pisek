from . import test_case
import unittest
import os
from ..compile import compile
from ..run import run
from ..task_config import TaskConfig


def resolve_extension(path, name):
    """
    Given a directory and `name`, finds a file named `name`.[ext],
    where [ext] is a file extension for one of the supported languages
    """
    extensions = [".cpp", ".py"]
    for ext in extensions:
        if os.path.isfile(os.path.join(path, name + ext)):
            return name + ext

    return None


def assertFileExists(self, path):
    self.assertTrue(
        os.path.isfile(os.path.join(self.task_dir, path)),
        "Ve složce úlohy musí existovat soubor '{}'".format(path),
    )


class ConfigIsValid(test_case.TestCase):
    def runTest(self):
        assertFileExists(self, "config")
        TaskConfig(self.task_dir)


class SampleExists(test_case.TestCase):
    def runTest(self):
        assertFileExists(self, "sample.in")
        assertFileExists(self, "sample.out")


class SolutionWorks(test_case.SolutionTestCase):
    def run_solution(self, executable, input_file):
        data_dir = os.path.join(self.task_dir, "data")
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        output_filename = "{}.{}.out".format(
            os.path.splitext(input_file[0], self.solution_name)
        )
        run(executable, input_file, os.path.join(data_dir, output_filename))

    def test_passes_sample(self, executable):
        self.run_solution(executable, os.path.join(self.task_dir, "sample.in"))

    def runTest(self):
        filename = resolve_extension(self.task_dir, self.solution_name)
        self.assertIsNotNone(
            filename, "Nepodařilo se najít řešení {}".format(self.solution_name)
        )
        executable = compile(os.path.join(self.task_dir, filename))
        self.assertIsNotNone(
            executable, "Chyba při kompilaci řešení {}".format(self.solution_name)
        )
        self.test_passes_sample(executable)


def kasiopea_test_suite(task_dir):
    suite = unittest.TestSuite()
    suite.addTest(ConfigIsValid(task_dir))
    suite.addTest(SampleExists(task_dir))

    config = TaskConfig(task_dir)

    for solution_name in config.solutions:
        suite.addTest(SolutionWorks(task_dir, solution_name))

    return suite
