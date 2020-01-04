import unittest
import os
import re

from . import test_case
from ..compile import compile
from ..generate import generate
from ..run import run
from ..task_config import TaskConfig
from ..diff import files_are_equal


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
        f"Ve složce úlohy musí existovat soubor '{path}'",
    )


class ConfigIsValid(test_case.TestCase):
    def runTest(self):
        assertFileExists(self, "config")
        TaskConfig(self.task_dir)


class SampleExists(test_case.TestCase):
    def runTest(self):
        assertFileExists(self, "sample.in")
        assertFileExists(self, "sample.out")


class GeneratorWorks(test_case.GeneratorTestCase):
    def runTest(self):
        filename = resolve_extension(self.task_dir, self.generator_name)
        self.assertIsNotNone(
            filename, f"Nepodařilo se najít generátor {self.generator_name}"
        )

        executable = compile(os.path.join(self.task_dir, filename))
        self.assertIsNotNone(
            executable, f"Chyba při kompilaci generátoru {self.generator_name}"
        )

        self.generate_any(executable)
        self.test_is_deterministic(executable)

    def generate_any(self, executable):
        data_dir = os.path.join(self.task_dir, "data/")
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        # easy
        easy_input_filename = os.path.join(data_dir, "tmp_easy.in")
        self.assertTrue(
            generate(executable, easy_input_filename, seed=1, isHard=False),
            f"Chyba při generování vstupu lehké verze se seedem 1",
        )

        easy_file_size = os.path.getsize(easy_input_filename)
        self.assertNotEqual(
            easy_file_size,
            0,
            f"Generátor vygeneroval prázdný vstup pro lehkou verzi se seedem 1",
        )

        # hard
        hard_input_filename = os.path.join(data_dir, "tmp_hard.in")
        self.assertTrue(
            generate(executable, hard_input_filename, seed=1, isHard=False),
            f"Chyba při generování těžké verze se seedem 1",
        )

        hard_file_size = os.path.getsize(easy_input_filename)
        self.assertNotEqual(
            hard_file_size,
            0,
            f"Generátor vygeneroval prázdný vstup pro lehkou verzi se seedem 1",
        )

    def test_is_deterministic(self, executable, N=20, seed=1):
        data_dir = os.path.join(self.task_dir, "data/")
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        # easy
        filenames = [
            os.path.join(data_dir, f"tmp_deterministic_easy_{i}.in") for i in range(N)
        ]
        for filename in filenames:
            self.assertTrue(
                generate(executable, filename, seed=seed, isHard=False),
                f"Chyba při generování vstupu lehké verze se seedem {seed}",
            )

        unequal_files = [
            filenames[i]
            for i in range(1, N)
            if not files_are_equal(filenames[0], filenames[i])
        ]
        self.assertListEqual(
            unequal_files, [], f"Generování lehké verze není deterministické"
        )

        # hard
        filenames = [
            os.path.join(data_dir, f"tmp_deterministic_hard_{i}.in") for i in range(N)
        ]
        for filename in filenames:
            self.assertTrue(
                generate(executable, filename, seed=seed, isHard=True),
                f"Chyba při generování vstupu těžké verze se seedem {seed}",
            )

        unequal_files = [
            filenames[i]
            for i in range(1, N)
            if not files_are_equal(filenames[0], filenames[i])
        ]
        self.assertListEqual(
            unequal_files, [], f"Generování těžké verze není deterministické"
        )


class SolutionWorks(test_case.SolutionTestCase):
    def run_solution(self, executable, input_file):
        data_dir = os.path.join(self.task_dir, "data/")
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        output_filename = "{}.{}.out".format(
            os.path.splitext(os.path.basename(input_file))[0], self.solution_name
        )
        output_file = os.path.join(data_dir, output_filename)

        self.assertTrue(
            run(executable, input_file, output_file),
            f"Chyba při spuštění {self.solution_name} na {input_file}",
        )
        return output_file

    def test_passes_sample(self, executable):
        sample_in = os.path.join(self.task_dir, "sample.in")
        sample_out = os.path.join(self.task_dir, "sample.out")
        output_filename = self.run_solution(executable, sample_in)
        self.assertTrue(
            files_are_equal(output_filename, sample_out),
            f"Špatná odpověď řešení {self.solution_name} na sample.in",
        )

    def expected_score(self) -> int:
        """
        solve -> 10
        solve_0b -> 0
        solve_jirka_4b -> 4
        """
        matches = re.findall(r"_([0-9]{1,2})b$", self.solution_name)
        if matches:
            assert len(matches) == 1
            score = int(matches[0])
            self.assertIn(
                score,
                [0, 4, 6, 10],
                f"Řešení {self.solution_name} by mělo získat {score} bodů, což nelze",
            )
            return score
        else:
            return 10

    def runTest(self):
        filename = resolve_extension(self.task_dir, self.solution_name)
        self.assertIsNotNone(
            filename, f"Nepodařilo se najít řešení {self.solution_name}"
        )
        executable = compile(os.path.join(self.task_dir, filename))
        self.assertIsNotNone(
            executable, f"Chyba při kompilaci řešení {self.solution_name}"
        )
        expected_score = self.expected_score()
        if expected_score == 10:
            # Solutions which don't pass one of the subtasks might not even pass the samples.
            # For example, the sample might contain tests which would not appear in the easy version
            self.test_passes_sample(executable)


def kasiopea_test_suite(task_dir):
    suite = unittest.TestSuite()
    suite.addTest(ConfigIsValid(task_dir))
    suite.addTest(SampleExists(task_dir))

    config = TaskConfig(task_dir)

    for solution_name in config.solutions:
        suite.addTest(SolutionWorks(task_dir, solution_name))

    suite.addTest(GeneratorWorks(task_dir, config.generator))

    return suite
