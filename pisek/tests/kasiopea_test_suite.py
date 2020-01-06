import unittest
import os
import re
from typing import Optional

from . import test_case
from ..task_config import TaskConfig
from .. import util
from ..generator import Generator


def assertFileExists(self, path):
    self.assertTrue(
        os.path.isfile(os.path.join(self.task_dir, path)),
        f"Ve složce úlohy musí existovat soubor '{path}'",
    )


def get_data_dir(task_dir):
    return os.path.join(task_dir, "data/")


class ConfigIsValid(test_case.TestCase):
    def runTest(self):
        assertFileExists(self, "config")
        TaskConfig(self.task_dir)


class SampleExists(test_case.TestCase):
    def runTest(self):
        assertFileExists(self, "sample.in")
        assertFileExists(self, "sample.out")


def generate_checked(
    case: test_case.GeneratorTestCase,
    seed: int,
    is_hard: bool,
    filename: Optional[str] = None,
) -> str:
    """
    If `filename` is not given, a reasonable name is chosen automatically.
    Then generates into `filename` and returns the file's path.
    """
    data_dir = get_data_dir(case.task_dir)
    if not filename:
        filename = f"{seed}_{int(is_hard)+1}.in"
    path = os.path.join(data_dir, filename)

    case.assertTrue(
        case.generator.generate(path, seed=seed, is_hard=is_hard),
        f"Chyba při generování vstupu {'těžké' if is_hard else 'lehké'} verze se seedem {seed}",
    )
    return path


class GeneratorWorks(test_case.GeneratorTestCase):
    def runTest(self):
        self.generate_any()
        self.test_respects_hex_seed()
        self.test_is_deterministic()

    def generate_any(self):
        data_dir = get_data_dir(self.task_dir)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        for is_hard in [False, True]:
            filename = generate_checked(self, seed=1, is_hard=is_hard)

            easy_file_size = os.path.getsize(filename)
            self.assertNotEqual(
                easy_file_size,
                0,
                "Generátor vygeneroval prázdný vstup pro"
                f"{'těžkou' if is_hard else 'lehkou'} verzi se seedem 1",
            )

    def test_respects_hex_seed(self):
        # Note: There is a small chance that 'FF' will really generate the same input as '0'.
        # TODO: this 'accidentally' also tests that different seeds generate different inputs
        #   (hexadecimal or otherwise), maybe we should test that more thoroughly

        data_dir = get_data_dir(self.task_dir)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        zero_filename = generate_checked(self, seed=0, is_hard=False)

        hexa = int("0xFF", 16)
        hexa_filename = generate_checked(self, seed=hexa, is_hard=False)

        self.assertFalse(
            util.files_are_equal(zero_filename, hexa_filename),
            "Generátor nerespektuje hexadecimální seed",
        )

    def test_is_deterministic(self, N=20, seed=1):
        data_dir = get_data_dir(self.task_dir)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        for is_hard in [False, True]:
            filenames = [
                generate_checked(
                    self,
                    seed,
                    is_hard,
                    filename=f"{seed}_{int(is_hard)+1}_iteration_{it}.in",
                )
                for it in range(N)
            ]
            unequal_files = [
                filenames[i]
                for i in range(1, N)
                if not util.files_are_equal(filenames[0], filenames[i])
            ]
            self.assertListEqual(
                unequal_files,
                [],
                f"Generování {'těžké' if is_hard else 'lehké'} verze není deterministické",
            )


class GeneratesInputs(test_case.GeneratorTestCase):
    def __init__(self, task_dir, generator, seeds):
        super().__init__(task_dir, generator)
        self.seeds = seeds

    def runTest(self):
        for is_hard in [False, True]:
            for seed in self.seeds:
                generate_checked(self, seed, is_hard)


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

    seeds = [1, 2, 3, 10, 123]
    generator = Generator(task_dir, config.generator)
    suite.addTest(GeneratorWorks(task_dir, generator))
    suite.addTest(GeneratesInputs(task_dir, generator, seeds))

    for solution_name in config.solutions:
        suite.addTest(SolutionWorks(task_dir, solution_name))

    return suite
