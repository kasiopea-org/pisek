import unittest
import os
import re
import random
from typing import Optional, Tuple, Dict, List

from . import test_case
from .test_case import assertFileExists
from ..task_config import TaskConfig
from .. import util
from ..solution import Solution
from ..generator import OnlineGenerator
from ..program import RunResult
from ..judge import WhiteDiffJudge


class SampleExists(test_case.TestCase):
    def runTest(self):
        assertFileExists(self, "sample.in")
        assertFileExists(self, "sample.out")


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
    data_dir = util.get_data_dir(case.task_dir)
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
    solution: Solution, seeds: List[int], timeout: int, quit_on_timeout: bool = True
) -> List[str]:
    """
    Generates all the possible outputs for the given seeds and subtasks.
    if `quit_on_timeout` is set, we assume that if the solution times out for a given seed,
    it will time out for others as well, so we don't run the solution on the other seeds
    """
    output_files = []
    data_dir = util.get_data_dir(solution.task_dir)
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

    for subtask in [1, 2]:
        for seed in seeds:
            path = os.path.join(data_dir, util.get_input_name(seed, subtask))
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

        data_dir = util.get_data_dir(self.task_dir)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        zero_filename = generate_checked(self, seed=0, subtask=1)

        hexa = int("0xFF", 16)
        hexa_filename = generate_checked(self, seed=hexa, subtask=1)

        self.assertFalse(
            util.files_are_equal(zero_filename, hexa_filename),
            "Generátor nerespektuje hexadecimální seed",
        )

    def test_is_deterministic(self, N=20, seed=1):
        data_dir = util.get_data_dir(self.task_dir)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        for subtask in [1, 2]:
            filenames = [
                generate_checked(
                    self,
                    seed,
                    subtask,
                    filename=f"{seed:x}_{int(subtask)}_iteration_{it}.in",
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
                f"Generování {'těžké' if (subtask == 2) else 'lehké'} verze není deterministické",
            )


class GeneratesInputs(test_case.GeneratorTestCase):
    def __init__(self, task_dir, generator, seeds):
        super().__init__(task_dir, generator)
        self.seeds = seeds

    def runTest(self):
        data_dir = util.get_data_dir(self.task_dir)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        for subtask in [1, 2]:
            for seed in self.seeds:
                generate_checked(self, seed, subtask)


class SolutionWorks(test_case.SolutionTestCase):
    def __init__(self, task_dir, solution_name, model_solution_name, seeds, timeout):
        super().__init__(task_dir, solution_name)
        self.model_solution_name = model_solution_name
        self.seeds = seeds
        self.run_config = {"timeout": timeout}
        self.expected_score = None
        self.judge = WhiteDiffJudge()

    def test_passes_sample(self):
        sample_in = os.path.join(self.task_dir, "sample.in")
        sample_out = os.path.join(self.task_dir, "sample.out")
        pts, verdict = self.judge.evaluate(
            self.solution, sample_in, sample_out, self.run_config
        )
        self.assertEqual(
            verdict.result,
            RunResult.OK,
            f"Chyba při spouštění {self.solution.name} na sample.in: {verdict}",
        )
        self.assertEqual(
            pts,
            1.0,
            f"Špatná odpověď řešení {self.solution.name} na sample.in: {verdict}",
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

    def get_score(self) -> Tuple[int, Dict[int, Tuple[int, str]]]:
        data_dir = util.get_data_dir(self.task_dir)

        total_score = 0

        # TODO: the subtask should be part of the key, not the value
        diffs: Dict[int, Tuple[int, str]] = {}  # seed -> (subtask, diff)

        for subtask_score, subtask in [(4, 1), (6, 2)]:
            ok = True
            for seed in self.seeds:
                output_filename = util.get_output_name(
                    util.get_input_name(seed, subtask), solution_name=self.solution.name
                )
                model_output_filename = util.get_output_name(
                    util.get_input_name(seed, subtask),
                    solution_name=self.model_solution_name,
                )
                output_file = os.path.join(data_dir, output_filename)
                model_output_file = os.path.join(data_dir, model_output_filename)

                if not util.files_are_equal(output_file, model_output_file):
                    ok = False

                    diffs[seed] = (
                        subtask,
                        "".join(
                            util.diff_files(
                                model_output_file,
                                output_file,
                                "správné řešení",
                                f"řešení solveru '{self.solution.name}'",
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

        generate_outputs(self.solution, self.seeds, self.run_config["timeout"])

        if self.solution.name != self.model_solution_name:
            score, diffs = self.get_score()
        else:
            # Maximum score and no diffs by definition
            score = 10
            diffs = None

        # TODO: make this a bit nicer
        formatted_diffs = (
            "\n".join(
                f"Diff seedu {seed:x} na obtížnosti "
                f"{'těžká' if (subtask == 2) else 'lehká'}:\n{diff}"
                for (seed, (subtask, diff)) in diffs.items()
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


def kasiopea_test_suite(
    task_dir: str,
    solutions: Optional[List[str]] = None,
    n_seeds=5,
    timeout=util.DEFAULT_TIMEOUT,
):
    """
    Tests a task. Generates test cases using the generator, then runs each solution
    in `solutions_to_test` (or all of them if `solutions == None`) and verifies
    that they get the expected number of points.
    """
    config = TaskConfig(task_dir)
    # Make sure we don't have stale files. We run this after loading `config`
    # to make sure `task_dir` is a valid task directory
    util.clear_data_dir(task_dir)

    suite = unittest.TestSuite()
    suite.addTest(test_case.ConfigIsValid(task_dir))
    suite.addTest(SampleExists(task_dir))

    random.seed(4)  # Reproducibility!
    seeds = random.sample(range(0, 16 ** 4), n_seeds)

    suite.addTest(GeneratorWorks(task_dir, generator))
    suite.addTest(GeneratesInputs(task_dir, generator, seeds))

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
                task_dir,
                solution_name,
                model_solution_name=(config.solutions[0]),
                seeds=seeds,
                timeout=timeout,
            )
        )

    return suite
