# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import glob
import unittest
import os
import sys
from typing import Optional, List

import termcolor

from . import test_case
from .test_case import SolutionWorks, Subtask, TaskInput
from ..task_config import TaskConfig
from .. import util
from ..generator import OfflineGenerator


def inputs_for_subtask(subtask_num: int, config: TaskConfig) -> List[TaskInput]:
    data_dir = config.get_data_dir()
    globs = config.subtasks[subtask_num].in_globs

    input_filenames: List[str] = []
    for g in globs:
        input_filenames += [
            os.path.basename(f) for f in glob.glob(os.path.join(data_dir, g))
        ]

    input_filenames.sort()

    return [TaskInput(f, subtask_num) for f in input_filenames]


def get_subtasks(task_config) -> List[Subtask]:
    subtasks = []

    for subtask_num in task_config.subtasks:
        score = task_config.subtasks[subtask_num].score
        inputs = inputs_for_subtask(subtask_num, task_config)
        subtasks.append(
            Subtask(score, inputs, subtask_num, task_config.subtasks[subtask_num].name)
        )

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
    only_necessary=False,  # True when testing a single solution
    strict=False,
    no_checker=False,
    all_tests: bool = False,
    **_ignored,  # Some arguments are relevant in kasiopea_test_suite but not here
):
    """
    Tests a task. Generates test cases using the generator, then runs each solution
    in `solutions` (or all of them if `solutions == None`) and verifies
    that they get the expected number of points.
    """

    config = TaskConfig(task_dir)

    suite = unittest.TestSuite()

    # Note that we can't just use `solutions` as the if-condition because we have to
    # distinguish between `[]` and `None`. Can we avoid this somehow?
    if solutions != []:
        # No need to check for samples when only testing generator
        suite.addTest(test_case.SampleExists(config))

    generator = OfflineGenerator(config, config.generator)
    suite.addTest(GeneratorWorks(config, generator))

    if not no_checker and not only_necessary:
        test_case.add_checker_cases(
            config,
            suite,
            in_self_test,
            get_subtasks=lambda: get_subtasks(config),
            strict=strict,
        )

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
        cur_timeout = timeout or config.get_timeout(i != 0)
        suite.addTest(
            SolutionWorks(
                config,
                solution_name,
                timeout=cur_timeout,
                get_subtasks=lambda: get_subtasks(config),
                in_self_test=in_self_test,
                all_tests=all_tests,
            )
        )

    return suite
