import shutil
import unittest
import os
import random
from typing import Optional, Tuple, Dict, List
import itertools

import tqdm

from . import test_case
from ..judge import Verdict
from ..task_config import TaskConfig
from .. import util
from ..solution import Solution
from ..generator import OnlineGenerator
from ..program import RunResult
from .. import judge


class SampleExists(test_case.TestCase):
    def runTest(self):
        self.assertFileExists("sample.in")
        self.assertFileExists("sample.out")

    def __str__(self):
        return f"Existuje ukázkový vstup a výstup"


class SampleNotEmpty(test_case.TestCase):
    def runTest(self):
        self.assertFileNotEmpty("sample.in")
        self.assertFileNotEmpty("sample.out")

    def __str__(self):
        return f"Ukázkový vstup a výstup je neprázdný"


def generate_checked(
    case: test_case.GeneratorTestCase,
    seed: int,
    subtask: int,
    filename: Optional[str] = None,
) -> str:
    """
    If `filename` is not given, a reasonable name is chosen automatically.
    Then generates into `filename` and returns the file's path.
    """
    data_dir = case.task_config.get_data_dir()
    if filename is None:
        filename = util.get_input_name(seed, subtask)
    path = os.path.join(data_dir, filename)

    case.assertTrue(
        case.generator.generate(path, seed=seed, subtask=subtask),
        f"Chyba při generování vstupu {'těžké' if (subtask == 2) else 'lehké'} verze"
        f" se seedem {seed:x}",
    )
    return path


def generate_outputs(
    solution: Solution,
    data_dir: str,
    seeds: List[int],
    timeout: int,
    quit_on_timeout: bool = True,
    in_self_test=False,
) -> List[str]:
    """
    Generates all the possible outputs for the given seeds and subtasks.
    if `quit_on_timeout` is set, we assume that if the solution times out for a given seed,
    it will time out for others as well, so we don't run the solution on the other seeds
    """
    output_files = []

    with tqdm.tqdm(
        total=len(seeds) * 2,
        desc=f"Běží řešení {solution.name}",
        disable=in_self_test,
    ) as pbar:
        for subtask in [1, 2]:
            for seed in seeds:
                path = os.path.join(data_dir, util.get_input_name(seed, subtask))
                result, output_file = solution.run_on_file(path, timeout)
                if quit_on_timeout and result == RunResult.TIMEOUT:
                    break

                if output_file is not None:
                    output_files.append(output_file)

                pbar.update(1)

    return output_files


class GeneratorWorks(test_case.GeneratorTestCase):
    def runTest(self):
        self.generate_any()
        self.test_respects_hex_seed()
        self.test_is_deterministic()

    def generate_any(self):
        for subtask in [1, 2]:
            filename = generate_checked(self, seed=1, subtask=subtask)

            easy_file_size = os.path.getsize(filename)
            self.assertNotEqual(
                easy_file_size,
                0,
                "Generátor vygeneroval prázdný vstup pro "
                f"{'těžkou' if (subtask == 2) else 'lehkou'} verzi se seedem 1",
            )

    def test_respects_hex_seed(self):
        # Note: There is a small chance that 'FF' will really generate the same input as '0'.
        # TODO: this 'accidentally' also tests that different seeds generate different inputs
        #   (hexadecimal or otherwise), maybe we should test that more thoroughly

        zero_filename = generate_checked(self, seed=0, subtask=1)

        hexa = int("0xFF", 16)
        hexa_filename = generate_checked(self, seed=hexa, subtask=1)

        self.assertFalse(
            util.files_are_equal(zero_filename, hexa_filename),
            "Generátor nerespektuje hexadecimální seed",
        )

    def test_is_deterministic(self, n=3, seed=1):
        for subtask in [1, 2]:
            filenames = [
                generate_checked(
                    self,
                    seed,
                    subtask,
                    filename=f"{seed:x}_{int(subtask)}_iteration_{it}.in",
                )
                for it in range(n)
            ]
            unequal_files = [
                filenames[i]
                for i in range(1, n)
                if not util.files_are_equal(filenames[0], filenames[i])
            ]
            self.assertListEqual(
                unequal_files,
                [],
                f"Generování {'těžké' if (subtask == 2) else 'lehké'} verze není deterministické",
            )

    def __str__(self):
        return f"Generátor {self.generator.name} funguje (je deterministický atd.)"


class GeneratesInputs(test_case.GeneratorTestCase):
    """
    Generates the inputs for the seeds we actually care about.
    """

    def __init__(self, task_config, generator, seeds, in_self_test=False):
        super().__init__(task_config, generator)
        self.seeds = seeds
        self.in_self_test = in_self_test

    def runTest(self):
        for seed in tqdm.tqdm(
            self.seeds, desc="Běží generátor", disable=self.in_self_test
        ):
            for subtask in [1, 2]:
                generate_checked(self, seed, subtask)

    def __str__(self):
        return f"Generátor {self.generator.name} vygeneruje vstupy"


class SolutionWorks(test_case.SolutionWorks):
    def __init__(
        self, task_config: TaskConfig, solution_name, timeout, seeds, in_self_test=False
    ):
        super().__init__(task_config, solution_name, timeout, in_self_test)
        self.seeds = seeds

    def get_subtasks(self):
        """
        For Kasiopea, each "subtask" consists of outputs generated for one
        of the variants (easy or hard), with the seeds we want to run on.
        Passing such a "subtask" means working correctly for all seeds considered.
        """
        subtasks = []

        for i, score in [(1, 4), (2, 6)]:
            inputs = []

            for seed in self.seeds:
                inputs.append(util.get_input_name(seed, i))

            subtasks.append((score, inputs))

        return subtasks


class JudgeHandlesWhitespace(test_case.TestCase):
    def __init__(self, task_config: TaskConfig):
        super().__init__(task_config)
        self.judge = judge.make_judge(task_config)
        self.model_solution = Solution(task_config.task_dir, task_config.solutions[0])

    def add_whitespace(self, file, n_spaces):
        with open(file, "r") as f:
            lines = f.readlines()

        lines_changed = [
            (line.strip("\r\n") + " ").replace(" ", " " * n_spaces) for line in lines
        ]

        with open(file, "w") as f:
            f.write("\r\n".join(lines_changed + ["  ", "    "]))

    def runTest(self):
        if not isinstance(self.judge, judge.KasiopeaExternalJudge):
            # This is only relevant for external judges.
            return

        sample_in = os.path.join(self.task_config.task_dir, "sample.in")
        sample_out = os.path.join(self.task_config.task_dir, "sample.out")
        sample_out_whitespaced = os.path.join(
            self.task_config.get_data_dir(), "sample_whitespaced.out"
        )
        shutil.copy2(sample_out, sample_out_whitespaced)

        result, output_file = self.model_solution.run_on_file(sample_in)
        self.assertEqual(result, RunResult.OK, "Vzorové řešení selhalo na sample.in")

        # To be sure, add different amounts of whitespace to each.
        self.add_whitespace(output_file, n_spaces=2)
        self.add_whitespace(sample_out_whitespaced, n_spaces=3)

        score, verdict = self.judge.evaluate_on_file(
            sample_in, sample_out_whitespaced, output_file
        )

        self.assertEqual(
            score,
            1,
            f"Judge {self.judge.name} neignoruje přebytečný whitespace"
            " nebo windowsovské konce řádků",
        )

    def __str__(self):
        return f"Judge správně řeší whitespace a konce řádku"


def kasiopea_test_suite(
    task_dir: str,
    solutions: Optional[List[str]] = None,
    n_seeds=5,
    timeout=util.DEFAULT_TIMEOUT,
    in_self_test=False,
    only_necessary=False,
):
    """
    Tests a task. Generates test cases using the generator, then runs each solution
    in `solutions` (or all of them if `solutions == None`) and verifies
    that they get the expected number of points.
    """
    config = TaskConfig(task_dir)
    data_dir = config.get_data_dir()
    util.clean_data_dir(task_dir)

    suite = unittest.TestSuite()

    if not only_necessary:
        if solutions != []:
            # No need to check for samples when only testing generator
            suite.addTest(SampleExists(config))
            suite.addTest(SampleNotEmpty(config))

    random.seed(4)  # Reproducibility!
    seeds = random.sample(range(0, 16 ** 4), n_seeds)

    generator = OnlineGenerator(task_dir, config.generator)

    if not only_necessary:
        suite.addTest(GeneratorWorks(config, generator))

    suite.addTest(GeneratesInputs(config, generator, seeds, in_self_test))
    suite.addTest(JudgeHandlesWhitespace(config))

    if solutions is None:
        solutions = config.solutions

    if not solutions:
        # This might be desirable if we only want to test the generator
        return suite

    if solutions[0] != config.solutions[0]:
        # Make sure that the model solution comes first even if we are not testing
        # all of the solutions
        solutions = [config.solutions[0]] + solutions

    for solution_name in solutions:
        suite.addTest(
            SolutionWorks(
                config,
                solution_name,
                seeds=seeds,
                timeout=timeout,
                in_self_test=in_self_test,
            )
        )

    return suite
