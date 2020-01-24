import unittest
import os
import re
import sys
import random
from typing import Optional, Tuple, Dict, List

from . import test_case
from ..task_config import TaskConfig
from .. import util
from ..solution import Solution
from ..generator import Generator
from ..program import RunResult


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


def get_input_name(seed: int, is_hard: bool) -> str:
    return util.get_input_name(seed, int(is_hard) + 1)


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
    data_dir = util.get_data_dir(case.task_dir)
    if not filename:
        filename = f"{seed:x}_{int(is_hard)+1}.in"
    path = os.path.join(data_dir, filename)

    case.assertTrue(
        case.generator.generate(path, seed=seed, is_hard=is_hard),
        f"Chyba při generování vstupu {'těžké' if is_hard else 'lehké'} verze se seedem {seed:x}",
    )
    return path


def generate_outputs(
    solution: Solution, seeds: List[int], timeout: int, quit_on_timeout: bool = True
) -> List[str]:
    """
    Generates all the possible outputs for the given seeds and subtasks.
    if `quit_on_timeout` is set, we assume that if the solution times out for a given seed,
    it will time out for others as well, and stop running it for the specific subtask
    """
    output_files = []
    data_dir = util.get_data_dir(solution.task_dir)
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

    for is_hard in [False, True]:  # subtasks
        for seed in seeds:
            path = os.path.join(data_dir, get_input_name(seed, is_hard))
            result, output_file = solution.run_on_file(path, timeout)
            if quit_on_timeout and result == RunResult.TIMEOUT:
                break

            if output_file is not None:
                output_files.append(output_file)

    return output_files


class GeneratorWorks(test_case.GeneratorTestCase):
    def runTest(self):
        self.generate_any()
        self.test_respects_hex_seed()
        self.test_is_deterministic()

    def generate_any(self):
        data_dir = util.get_data_dir(self.task_dir)
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

        data_dir = util.get_data_dir(self.task_dir)
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
        data_dir = util.get_data_dir(self.task_dir)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        for is_hard in [False, True]:
            filenames = [
                generate_checked(
                    self,
                    seed,
                    is_hard,
                    filename=f"{seed:x}_{int(is_hard)+1}_iteration_{it}.in",
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
        data_dir = util.get_data_dir(self.task_dir)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        for is_hard in [False, True]:
            for seed in self.seeds:
                generate_checked(self, seed, is_hard)


class SolutionWorks(test_case.SolutionTestCase):
    def __init__(self, task_dir, solution_name, model_solution_name, seeds, timeout):
        super().__init__(task_dir, solution_name)
        self.model_solution_name = model_solution_name
        self.seeds = seeds
        self.timeout = timeout
        self.expected_score = None

    def test_passes_sample(self):
        sample_in = os.path.join(self.task_dir, "sample.in")
        sample_out = os.path.join(self.task_dir, "sample.out")
        result, output_file = self.solution.run_on_file(sample_in, self.timeout)
        self.assertEqual(
            result,
            RunResult.OK,
            f"Chyba při spouštění {self.solution.name} na sample.in",
        )
        self.assertTrue(
            util.files_are_equal(output_file, sample_out),
            f"Špatná odpověď řešení {self.solution.name} na sample.in",
        )

    def get_expected_score(self) -> int:
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

    def get_score(self) -> Tuple[int, Dict[int, Tuple[bool, str]]]:
        data_dir = util.get_data_dir(self.task_dir)

        total_score = 0
        diffs: Dict[int, Tuple[bool, str]] = {}  # seed -> (is_hard, diff)

        for subtask_score, is_hard in [(4, False), (6, True)]:
            ok = True
            for seed in self.seeds:
                output_filename = util.get_output_name(
                    get_input_name(seed, is_hard), solution_name=self.solution.name
                )
                model_output_filename = util.get_output_name(
                    get_input_name(seed, is_hard),
                    solution_name=self.model_solution_name,
                )
                output_file = os.path.join(data_dir, output_filename)
                model_output_file = os.path.join(data_dir, model_output_filename)

                if not util.files_are_equal(output_file, model_output_file):
                    ok = False

                    diffs[seed] = (
                        is_hard,
                        "".join(
                            util.diff_files(
                                model_output_file,
                                output_file,
                                "správné řešení",
                                "řešení solveru '{self.solution.name}'",
                            )
                        ),
                    )

            if ok:
                total_score += subtask_score

        return total_score, diffs

    def runTest(self):
        self.solution.compile()
        self.expected_score = self.get_expected_score()
        if self.expected_score == 10:
            # Solutions which don't pass one of the subtasks might not even pass the samples.
            # For example, the sample might contain tests which would not appear in the easy version
            self.test_passes_sample()

        generate_outputs(self.solution, self.seeds, self.timeout)

        if self.solution.name != self.model_solution_name:
            score, diffs = self.get_score()
        else:
            # Maximum score and no diffs by definition
            score = 10
            diffs = None

        # TODO: make this a bit nicer
        formatted_diffs = (
            "\n".join(
                f"Diff seedu {seed:x} na obtížnosti {'těžká' if is_hard else 'lehká'}:\n{diff}"
                for (seed, (is_hard, diff)) in diffs.items()
            )
            if diffs is not None
            else ""
        )

        self.assertEqual(
            score,
            self.expected_score,
            f"Řešení {self.solution.name} mělo získat {self.expected_score}b,"
            f" ale získalo {score}b\n{formatted_diffs}",
        )


# used for adding a dependency to model solution
# subsumed by SolutionWorks which is more general
class SolutionOutputs(test_case.SolutionTestCase):
    def __init__(self, task_dir, solution_name, seeds, timeout):
        super().__init__(task_dir, solution_name)
        self.seeds = seeds
        self.timeout = timeout

    def runTest(self):
        self.solution.compile_if_needed()
        generate_outputs(self.solution, self.seeds, self.timeout)


def kasiopea_test_suite(task_dir, timeout=util.DEFAULT_TIMEOUT):
    """
    Tests the complete task:
    all solutions, the generator,
    config, sample inputs/outputs, etc.
    """

    suite = unittest.TestSuite()
    suite.addTest(ConfigIsValid(task_dir))
    suite.addTest(SampleExists(task_dir))

    config = TaskConfig(task_dir)

    seeds = [1, 2, 3, 10, 123]
    generator = Generator(task_dir, config.generator)
    suite.addTest(GeneratorWorks(task_dir, generator))
    suite.addTest(GeneratesInputs(task_dir, generator, seeds))

    for solution_name in config.solutions:
        suite.addTest(
            SolutionWorks(
                task_dir,
                solution_name,
                model_solution_name=(config.solutions[0]),
                seeds=seeds,
                timeout=timeout,
            )
        )

    return suite


def solution_test_suite(task_dir, solution_name, n, timeout=util.DEFAULT_TIMEOUT):
    """
    Tests _only_ the solution! (minimal test)
    Cannot test the correctness of the first solver in config.
    """
    suite = unittest.TestSuite()

    config = TaskConfig(task_dir)

    seeds = random.sample(range(0, 16 ** 4), n)

    generator = Generator(task_dir, config.generator)
    suite.addTest(GeneratesInputs(task_dir, generator, seeds))

    # Generate the gold data from the first (model/gold) solution
    suite.addTest(SolutionOutputs(task_dir, config.solutions[0], seeds, timeout))

    suite.addTest(
        SolutionWorks(
            task_dir,
            solution_name,
            model_solution_name=(config.solutions[0]),
            seeds=seeds,
        )
    )

    return suite


def generator_test_suite(task_dir):
    """
    Tests _only_ the generator!
    """
    suite = unittest.TestSuite()

    config = TaskConfig(task_dir)

    seeds = [1, 2, 3, 10, 123]
    generator = Generator(task_dir, config.generator)
    suite.addTest(GeneratorWorks(task_dir, generator))
    suite.addTest(GeneratesInputs(task_dir, generator, seeds))

    return suite
