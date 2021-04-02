import glob
import unittest
import os
from typing import Optional, List

import termcolor

from . import test_case
from .test_case import SolutionWorks, Subtask
from ..task_config import TaskConfig
from .. import util
from ..generator import OfflineGenerator


def inputs_for_subtask(subtask: int, config: TaskConfig):
    data_dir = config.get_data_dir()
    globs = config.subtasks[subtask].in_globs

    res: List[str] = []
    for g in globs:
        res += [os.path.basename(f) for f in glob.glob(os.path.join(data_dir, g))]

    return sorted(res)


def get_subtasks(task_config) -> List[Subtask]:
    subtasks = []

    for subtask in task_config.subtasks:
        score = task_config.subtasks[subtask].score
        inputs = inputs_for_subtask(subtask, task_config)
        subtasks.append(Subtask(score, inputs, task_config.subtasks[subtask].name))

    return subtasks


class GeneratorWorks(test_case.GeneratorTestCase):
    def __init__(self, task_config, generator: OfflineGenerator):
        super().__init__(task_config, generator)

    def runTest(self):
        data_dir = self.task_config.get_data_dir()
        return_code = self.generator.generate(test_dir=data_dir)

        self.assertTrue(return_code == 0, f"Chyba při generování vstupu.")

        test_files = glob.glob(os.path.join(data_dir, "*.in"))
        self.assertTrue(test_files, f"Generátor nevygeneroval žádné vstupní soubory.")

        for subtask in self.task_config.subtasks:
            self.assertTrue(
                inputs_for_subtask(subtask, self.task_config),
                f"Chybí vstupní soubory pro subtask {subtask}.",
            )

        if self.generator.cache_used:
            message = "\n  Generátor se nezměnil, používám vstupy vygenerované v předchozím běhu."
            print(termcolor.colored(message, color="cyan"))

    def __str__(self):
        return f"Generátor {self.generator.name} funguje"


def cms_test_suite(
    task_dir: str,
    solutions: Optional[List[str]] = None,
    timeout=None,
    in_self_test=False,
    **_ignored,  # Some arguments are relevant in kasiopea_test_suite but not here
):
    """
    Tests a task. Generates test cases using the generator, then runs each solution
    in `solutions` (or all of them if `solutions == None`) and verifies
    that they get the expected number of points.
    """

    config = TaskConfig(task_dir)
    util.clean_data_dir(config, leave_inputs=True)

    if timeout is None:
        timeout = config.timeout_other_solutions or util.DEFAULT_TIMEOUT

    timeout_model_solution = config.timeout_model_solution or timeout

    suite = unittest.TestSuite()

    if solutions:
        # No need to check for samples when only testing generator
        suite.addTest(test_case.SampleExists(config.get_samples_dir()))

    generator = OfflineGenerator(config, config.generator)
    suite.addTest(GeneratorWorks(config, generator))

    if solutions is None:
        solutions = config.solutions

    if not solutions:
        # This might be desirable if we only want to test the generator
        return suite

    if solutions[0] != config.solutions[0]:
        # Make sure that the model solution comes first even if we are not testing
        # all of the solutions
        solutions = [config.solutions[0]] + solutions

    for i, solution_name in enumerate(solutions):
        cur_timeout = timeout_model_solution if i == 0 else timeout
        suite.addTest(
            SolutionWorks(
                config,
                solution_name,
                timeout=cur_timeout,
                get_subtasks=lambda: get_subtasks(config),
                in_self_test=in_self_test,
            )
        )

    return suite
