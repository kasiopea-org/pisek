import unittest
import os
import re
import random
from typing import Optional, Tuple, Dict, List

from . import test_case
from ..task_config import TaskConfig
from .. import util
from ..generator import OfflineGenerator
from ..judge import ExternalJudge
from ..program import Program, RunResult


class GeneratorWorks(test_case.GeneratorTestCase):
    def runTest(self):
        data_dir = util.get_data_dir(self.task_dir)
        self.assertTrue(
            self.generator.generate(test_dir=data_dir), f"Chyba při generování vstupu.",
        )

    def __str__(self):
        return f"Generátor {self.generator.name} funguje"


class SolutionWorks(test_case.SolutionTestCase):
    def __init__(self, task_dir, solution_name, timeout):
        super().__init__(task_dir, solution_name)
        self.run_config = {"timeout": timeout}
        self.judge = ExternalJudge(Program(self.task_dir, "judge"))

    def runTest(self):
        # TODO: get correct judge based on the config
        self.test_passes_samples()

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


def cms_test_suite(
    task_dir: str,
    solutions: Optional[List[str]] = None,
    timeout=util.DEFAULT_TIMEOUT,
    **kwargs,
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
    suite.addTest(test_case.SampleExists(task_dir))

    generator = OfflineGenerator(task_dir, config.generator)
    suite.addTest(GeneratorWorks(task_dir, generator))
    if solutions:
        suite.addTest(SolutionWorks(task_dir, solutions[0], timeout))

    return suite
