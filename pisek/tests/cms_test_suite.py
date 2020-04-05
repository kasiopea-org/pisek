import glob
import unittest
import os
import re
import random
from typing import Optional, Tuple, Dict, List

from pisek.solution import Solution
from . import test_case
from ..task_config import TaskConfig
from .. import util
from ..generator import OfflineGenerator
from ..judge import ExternalJudge, make_judge, Judge
from ..program import Program, RunResult


def inputs_for_subtask(subtask: int, task_dir: str, config: TaskConfig):
    data_dir = util.get_data_dir(task_dir)
    globs = config.subtasks[subtask].in_globs

    res: List[str] = []
    for g in globs:
        res += [os.path.basename(f) for f in glob.glob(os.path.join(data_dir, g))]

    return sorted(res)


class GeneratorWorks(test_case.GeneratorTestCase):
    def __init__(self, task_dir, generator, config: TaskConfig):
        super().__init__(task_dir, generator)
        self.config = config

    def runTest(self):
        data_dir = util.get_data_dir(self.task_dir)
        self.assertTrue(
            self.generator.generate(test_dir=data_dir), f"Chyba při generování vstupu.",
        )

        test_files = glob.glob(os.path.join(data_dir, "*.in"))
        self.assertTrue(test_files, "Generátor nevygeneroval žádné vstupní soubory")

        for subtask in self.config.subtasks:
            self.assertTrue(
                inputs_for_subtask(subtask, self.task_dir, self.config),
                f"Chybí vstupní soubory pro subtask {subtask}",
            )

    def __str__(self):
        return f"Generátor {self.generator.name} funguje"


class SolutionWorks(test_case.SolutionTestCase):
    def __init__(self, task_dir, solution_name, timeout):
        super().__init__(task_dir, solution_name)
        self.run_config = {"timeout": timeout}
        self.task_config = TaskConfig(self.task_dir)
        self.judge = make_judge(self.task_dir, self.task_config)

    def test_passes_samples(self):
        for sample_in, sample_out in util.get_samples(self.task_dir):
            pts, verdict = self.judge.evaluate(
                self.solution, sample_in, sample_out, self.run_config
            )
            self.assertEqual(
                verdict.result,
                RunResult.OK,
                f"Chyba při spouštění {self.solution.name} na {sample_in}: {verdict}",
            )
            self.assertEqual(
                pts,
                1.0,
                f"Špatná odpověď řešení {self.solution.name} na {sample_in}: {verdict}",
            )

    def get_subtask_score(self, subtask):
        data_dir = util.get_data_dir(self.task_dir)
        inputs = inputs_for_subtask(subtask, self.task_dir, self.task_config)
        model_solution_name = self.task_config.solutions[0]

        # TODO: possible optimization for the model solution?
        judge_score = 1.0
        for input_file in inputs:
            model_output_filename = util.get_output_name(
                input_file, solution_name=model_solution_name,
            )

            pts, verdict = self.judge.evaluate(
                self.solution,
                input_file=os.path.join(data_dir, input_file),
                correct_output=os.path.join(data_dir, model_output_filename),
                run_config=self.run_config,
            )

            judge_score = min(judge_score, pts)

            if judge_score == 0:
                break

        return judge_score

    def runTest(self):
        data_dir = util.get_data_dir(self.task_dir)
        expected_score = util.get_expected_score(self.solution.name, self.task_config)
        max_score = self.task_config.get_maximum_score()

        if expected_score == max_score:
            # Solutions which don't pass one of the subtasks might not even pass
            # the samples. For example, the sample might contain tests which would
            # not appear in the easy version
            self.test_passes_samples()

        score = 0
        for subtask in self.task_config.subtasks:
            max_subtask_score = self.task_config.subtasks[subtask].score
            judge_score = self.get_subtask_score(subtask)
            score += judge_score * max_subtask_score

        score = round(score)

        # TODO: add diffs
        self.assertEqual(
            score,
            expected_score,
            f"Řešení {self.solution.name} mělo získat {expected_score}b,"
            f" ale získalo {score}b",
        )

    def __str__(self):
        return "Řešení {} získá {}b".format(
            self.solution.name,
            util.get_expected_score(self.solution.name, self.task_config),
        )


def cms_test_suite(
    task_dir: str,
    solutions: Optional[List[str]] = None,
    timeout=util.DEFAULT_TIMEOUT,
    **kwargs,
):
    """
    Tests a task. Generates test cases using the generator, then runs each solution
    in `solutions` (or all of them if `solutions == None`) and verifies
    that they get the expected number of points.
    """

    config = TaskConfig(task_dir)
    util.clean_data_dir(task_dir)

    suite = unittest.TestSuite()
    suite.addTest(test_case.ConfigIsValid(task_dir))
    suite.addTest(test_case.SampleExists(task_dir))

    generator = OfflineGenerator(task_dir, config.generator)
    suite.addTest(GeneratorWorks(task_dir, generator, config))

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
        suite.addTest(SolutionWorks(task_dir, solution_name, timeout=timeout))

    return suite
