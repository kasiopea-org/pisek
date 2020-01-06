import unittest
import os
import re

from . import test_case
from ..task_config import TaskConfig
from .. import util


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
        self.generate_any()
        self.test_respects_hex_seed()
        self.test_is_deterministic()

    def generate_any(self):
        data_dir = os.path.join(self.task_dir, "data/")
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        # easy
        easy_input_filename = os.path.join(data_dir, "tmp_easy.in")
        self.assertTrue(
            self.generator.generate(easy_input_filename, seed=1, is_hard=False),
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
            self.generator.generate(hard_input_filename, seed=1, is_hard=False),
            f"Chyba při generování těžké verze se seedem 1",
        )

        hard_file_size = os.path.getsize(easy_input_filename)
        self.assertNotEqual(
            hard_file_size,
            0,
            f"Generátor vygeneroval prázdný vstup pro lehkou verzi se seedem 1",
        )

    def test_respects_hex_seed(self):
        # Poznámka:
        # Tady je malá šance, že 'FF' fakt vygeneruje to samý jako '0'.

        data_dir = os.path.join(self.task_dir, "data/")
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        zero_filename = os.path.join(data_dir, "tmp_zero.in")
        self.assertTrue(
            self.generator.generate(zero_filename, seed=0, is_hard=False),
            f"Chyba při generování vstupu lehké verze se seedem 0",
        )

        hexa = int("0xFF", 16)

        hexa_filename = os.path.join(data_dir, "tmp_hexa.in")
        self.assertTrue(
            self.generator.generate(hexa_filename, seed=hexa, is_hard=False),
            f"Chyba při generování vstupu lehké verze se seedem {hexa:x}",
        )

        self.assertFalse(
            util.files_are_equal(zero_filename, hexa_filename),
            "Generátor nerespektuje hexadecimální seed",
        )

    def test_is_deterministic(self, N=20, seed=1):
        data_dir = os.path.join(self.task_dir, "data/")
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        # easy
        filenames = [
            os.path.join(data_dir, f"tmp_deterministic_easy_{i}.in") for i in range(N)
        ]
        for filename in filenames:
            self.assertTrue(
                self.generator.generate(filename, seed=seed, is_hard=False),
                f"Chyba při generování vstupu lehké verze se seedem {seed}",
            )

        unequal_files = [
            filenames[i]
            for i in range(1, N)
            if not util.files_are_equal(filenames[0], filenames[i])
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
                self.generator.generate(filename, seed=seed, is_hard=True),
                f"Chyba při generování vstupu těžké verze se seedem {seed}",
            )

        unequal_files = [
            filenames[i]
            for i in range(1, N)
            if not util.files_are_equal(filenames[0], filenames[i])
        ]
        self.assertListEqual(
            unequal_files, [], f"Generování těžké verze není deterministické"
        )


class SolutionWorks(test_case.SolutionTestCase):
    def test_passes_sample(self):
        sample_in = os.path.join(self.task_dir, "sample.in")
        sample_out = os.path.join(self.task_dir, "sample.out")
        output_file = self.solution.run_on_file(sample_in)
        self.assertIsNotNone(
            output_file, f"Chyba při spouštění {self.solution.name} na sample.in"
        )
        self.assertTrue(
            util.files_are_equal(output_file, sample_out),
            f"Špatná odpověď řešení {self.solution.name} na sample.in",
        )

    def expected_score(self) -> int:
        """
        solve -> 10
        solve_0b -> 0
        solve_jirka_4b -> 4
        """
        matches = re.findall(r"_([0-9]{1,2})b$", self.solution.name)
        if matches:
            assert len(matches) == 1
            score = int(matches[0])
            self.assertIn(
                score,
                [0, 4, 6, 10],
                f"Řešení {self.solution.name} by mělo získat {score} bodů, což nelze",
            )
            return score
        else:
            return 10

    def runTest(self):
        self.solution.compile()
        expected_score = self.expected_score()
        if expected_score == 10:
            # Solutions which don't pass one of the subtasks might not even pass the samples.
            # For example, the sample might contain tests which would not appear in the easy version
            self.test_passes_sample()


def kasiopea_test_suite(task_dir):
    suite = unittest.TestSuite()
    suite.addTest(ConfigIsValid(task_dir))
    suite.addTest(SampleExists(task_dir))

    config = TaskConfig(task_dir)

    for solution_name in config.solutions:
        suite.addTest(SolutionWorks(task_dir, solution_name))

    suite.addTest(GeneratorWorks(task_dir, config.generator))

    return suite
