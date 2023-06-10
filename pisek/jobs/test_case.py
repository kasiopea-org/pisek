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

import os
import sys
import unittest
import shutil
from typing import List, Tuple, Optional, Callable, Dict

import termcolor
import tqdm

from ..checker import Checker
from ..program import RunResultKind
from ..task_config import TaskConfig
from ..solution import Solution
from ..judge import CMSExternalJudge, KasiopeaExternalJudge, make_judge, Judge
from .. import util


class TestCase(unittest.TestCase):
    def __init__(self, task_config: TaskConfig):
        super().__init__()
        self.task_config = task_config

    def log(self, msg, *args, **kwargs):
        print(msg, file=sys.stderr, *args, **kwargs)
        sys.stderr.flush()

    def assertFileExists(self, path):
        self.assertTrue(
            os.path.isfile(os.path.join(self.task_config.task_dir, path)),
            f"Ve složce úlohy musí existovat soubor '{path}'",
        )

    def assertFileNotEmpty(self, path):
        # Assumes that the file already exists!
        self.assertTrue(
            os.path.getsize(os.path.join(self.task_config.task_dir, path)) > 0,
            f"Ve složce úlohy musí být neprázdný soubor '{path}'",
        )


class SolutionTestCase(TestCase):
    def __init__(self, task_config: TaskConfig, solution_name):
        super().__init__(task_config)
        self.solution = Solution(task_config, solution_name)


class GeneratorTestCase(TestCase):
    def __init__(self, task_config: TaskConfig, generator):
        super().__init__(task_config)
        self.generator = generator


# Non-abstract test-cases common to multiple contest types.


class SampleExists(TestCase):
    def runTest(self):
        samples = util.get_samples(self.task_config.get_samples_dir())
        self.assertGreater(
            len(samples),
            0,
            f"V podsložce {self.task_config.samples_subdir} složky s úlohou nejsou žádné samply "
            "(soubory tvaru sample*.in s odpovídajícím sample*.out)",
        )
        for sample_in, sample_out in samples:
            self.assertTrue(
                os.path.isfile(sample_in),
                f"Vzorový vstup neexistuje nebo není soubor: {sample_in}",
            )
            self.assertTrue(
                os.path.isfile(sample_out),
                f"Vzorový výstup neexistuje nebo není soubor: {sample_out}",
            )


class TaskInput:
    def __init__(
        self,
        input_filename: str,
        subtask_num: int,
        output_filename: Optional[str] = None,
        seed: Optional[int] = None,
    ):
        """
        An input for a task, meant to test solutions.

        :param input_filename: The name of the input file in the data directory.
        :param subtask_num: The input's subtask number.
            Kasiopea uses 1 for easy, 2 for hard.
        :param output_filename: The name of the correct output file in the data directory.
        :param seed: The seed that was used to generate this input.
            Only relevant for Kasiopea.
        """
        self.input_filename = input_filename
        self.subtask_num = subtask_num
        self.output_filename = output_filename
        self.seed = seed


class Subtask:
    def __init__(
        self,
        score: int,
        inputs: List[TaskInput],
        subtask_num: int,
        name: Optional[str] = None,
    ):
        """
        A collection of TaskInputs along with metadata.

        :param score: The score given for completing the subtask (solving all TaskInputs).
        :param inputs: A list of the inputs making up the Subtask.
        :param subtask_num: The subtask's number. Kasiopea uses 1 for easy, 2 for hard.
        :param name: An optional human-readable identifier of the task.
        """
        self.score = score
        self.inputs = inputs

        # Make sure the data is consistent
        for inp in self.inputs:
            assert inp.subtask_num == subtask_num

        self.subtask_num = subtask_num
        self.name = name


class SolutionWorks(SolutionTestCase):
    """
    Tests if a specific solution gets the correct score.
    """

    def __init__(
        self,
        task_config: TaskConfig,
        solution_name,
        timeout,
        get_subtasks: Callable[[], List[Subtask]],
        in_self_test=False,
        all_tests=False,
    ):
        super().__init__(task_config, solution_name)
        self.run_config = {"timeout": timeout}
        self.judge: Judge = make_judge(self.task_config)
        self.in_self_test = in_self_test
        self.all_tests = all_tests

        # Subtasks might not be available when this test case is created, so we need to
        # pass a function to get them later
        self.get_subtasks = get_subtasks

    def test_passes_samples(self):
        samples_dir = self.task_config.get_samples_dir()
        data_dir = self.task_config.get_data_dir()

        inputs = []

        for sample_in, sample_out in util.get_samples(samples_dir):
            data_sample_in = os.path.join(data_dir, os.path.basename(sample_in))
            data_sample_out = os.path.join(data_dir, os.path.basename(sample_out))
            # Copy the samples into the data (tests) directory for consistency
            # with the other tests
            shutil.copy(sample_in, data_sample_in)
            shutil.copy(sample_out, data_sample_out)

            inputs.append(
                TaskInput(
                    input_filename=os.path.basename(sample_in),
                    output_filename=os.path.basename(sample_out),
                    # We set subtask_num=1 (easy version) because there is no way to know
                    # which subtask the sample belongs to. Sometimes the sample output
                    # might only solve the easy version and then treating it as the
                    # optimal solution might give the wrong answer
                    # (e.g. Kasiopea - domaci kolo 2021, uloha I).
                    subtask_num=1,
                    # The sample corresponds to no seed, so we just use a dummy value
                    seed=0,
                )
            )

        score, message = self.get_score_for_inputs(inputs)

        self.assertEqual(
            score,
            1,
            f"Řešení {self.solution.name} nefunguje na samplu/samplech."
            f"\n{message or ''}",
        )

    def get_score_for_inputs(
        self, inputs: List[TaskInput]
    ) -> Tuple[float, Optional[str]]:
        """
        Runs the solution on a list of TaskInputs.

        Returns a tuple of (score, message), where:

        - score is the minimum score awarded by the judge for these inputs.
          The judge score is in [0.0, 1.0] (possibly non-integral for CMS).

        - message contains information about what, if anything, went wrong
        """
        data_dir = self.task_config.get_data_dir()
        model_solution_name = self.task_config.solutions[0]

        judge_score = 1.0
        messages = []

        for inp in inputs:
            if not inp.output_filename:
                inp.output_filename = util.get_output_name(
                    inp.input_filename, solution_name=model_solution_name
                )

            if inp.seed is not None:
                # The seed is passed as a hexadecimal string.
                judge_args = [str(inp.subtask_num), f"{inp.seed:x}"]
            else:
                # No seed means we are not in Kasiopea, so judge_args are not used.
                # Simply pass nothing.
                judge_args = []

            pts, run_result = self.judge.evaluate(
                self.solution,
                input_file=os.path.join(data_dir, inp.input_filename),
                correct_output=os.path.join(data_dir, inp.output_filename),
                run_config=self.run_config,
                judge_args=judge_args,
            )

            if run_result.kind == RunResultKind.OK:
                c = "·" if pts == 1 else "W" if pts == 0 else f"[{pts:.2f}]"

                if pts != 1 and run_result.msg:
                    messages.append(run_result.msg)

            else:
                result_chars = {
                    RunResultKind.TIMEOUT: "T",
                    RunResultKind.RUNTIME_ERROR: "!",
                }

                c = result_chars[run_result.kind]

                if run_result.msg is not None:
                    messages.append(run_result.msg)

            self.log(c, end="")

            judge_score = min(judge_score, pts)

            if judge_score == 0 and not self.all_tests:
                break  # Fail fast

        return judge_score, ("\n".join(messages) if messages else None)

    def runTest(self):
        expected_score = util.get_expected_score(self.solution.name, self.task_config)
        max_score = self.task_config.get_maximum_score()

        if expected_score == max_score:
            # Solutions which don't pass one of the subtasks might not even pass
            # the samples. For example, the sample might contain tests which would
            # not appear in the easy version
            self.test_passes_samples()

        score = 0
        messages = []
        for subtask in self.get_subtasks():
            self.log("|", end="")
            judge_score, message = self.get_score_for_inputs(subtask.inputs)

            # Note that this may be non-integral
            score += judge_score * subtask.score

            if message:
                messages.append(message)

        self.log("| ", end="")

        # TODO: document this somewhere
        score = round(score * 100) / 100

        if expected_score is not None:
            if score > expected_score:
                # If the solution works too well (e.g. 4 points instead of 0),
                # printing diffs of wrong answers does not make sense.
                message = ""
            else:
                message = "\n".join(messages)

            self.assertEqual(
                score,
                expected_score,
                f"Řešení {self.solution.name} mělo získat {expected_score}b,"
                f" ale získalo {score}b.\n{message}",
            )
        else:
            self.log(f"{score}b ", end="")

    def __str__(self):
        expected_score = util.get_expected_score(self.solution.name, self.task_config)
        if expected_score is None:
            expected_score_str = "nespecifikovaný počet bodů"
        else:
            expected_score_str = f"{expected_score}b"
        return f"Řešení {self.solution.name} získá {expected_score_str}"

    def log(self, msg, *args, **kwargs):
        if not self.in_self_test:
            super().log(msg, *args, **kwargs)


class CheckerDistinguishesSubtasks(TestCase):
    """
    Makes sure the checker gives different results for different subtasks.
    Specifically, for subtask i, runs the checker on the inputs for subtask i but tells
    it that the subtask is (i-1).
    The check should therefore not pass for at least one of the inputs.
    """

    def __init__(
        self, task_config, checker: Checker, get_subtasks: Callable[[], List[Subtask]]
    ):
        super().__init__(task_config)
        self.checker = checker
        self.get_subtasks = get_subtasks

    def runTest(self):
        subtasks = self.get_subtasks()
        last_inputs = set()
        last_subtask_num = None

        for subtask in subtasks:
            new_inputs = set(inp.input_filename for inp in subtask.inputs) - last_inputs
            subtask_num = subtask.subtask_num

            if last_subtask_num is None:
                # Nothing to compare with at this point.
                last_subtask_num = subtask_num
                continue

            failed = False

            for input_file in new_inputs:
                res = self.checker.run_on_file(input_file, last_subtask_num)

                if res.returncode != 0:
                    failed = True

            self.assertTrue(
                failed,
                (
                    f"Checker '{self.checker.name}' není dost přísný: "
                    f"nestěžuje si, když přidáme vstupy ze subtasku {subtask_num}"
                    f" do subtasku {last_subtask_num}. Subtask {last_subtask_num} "
                    "má přitom přísnější omezení (tj. je snažší) "
                    f"takže vstupy ze subtasku {subtask_num} by neměly být "
                    f"platné pro subtask {last_subtask_num}."
                ),
            )

            last_inputs = set(subtask.inputs)
            last_subtask_num = subtask_num

    def __str__(self):
        return f"Checker {self.checker.name} rozliší subtasky"


class InputsPassChecker(TestCase):
    """If a checker program is specified in the task config, runs the checker."""

    def __init__(
        self,
        task_config,
        checker: Checker,
        get_subtasks: Callable[[], List[Subtask]],
        in_self_test: bool,
    ):
        super().__init__(task_config)
        self.checker = checker
        self.get_subtasks = get_subtasks
        self.in_self_test = in_self_test

    def runTest(self):
        subtasks = self.get_subtasks()

        all_inputs = []
        for subtask in subtasks:
            all_inputs += subtask.inputs

        for inp in tqdm.tqdm(
            all_inputs,
            desc=f"Běží checker '{self.checker.name}'",
            disable=self.in_self_test,
        ):
            res = self.checker.run_on_file(inp.input_filename, inp.subtask_num)

            self.assertEqual(
                res.returncode,
                0,
                (
                    f"Checker '{self.checker.name}' neprošel "
                    f"pro vstup {inp.input_filename} "
                    f"subtasku {inp.subtask_num}.\n{util.quote_process_output(res)}"
                ),
            )

    def __str__(self):
        return f"Vygenerované vstupy projdou checkerem {self.checker.name}"


def add_checker_cases(
    task_config: TaskConfig,
    suite: unittest.TestSuite,
    in_self_test: bool,
    get_subtasks,
    strict: bool,
):
    if not task_config.checker:
        if strict:
            print(
                f"V configu úlohy {task_config.task_dir} není specifikovaný checker.",
                file=sys.stderr,
            )
            exit(1)
        if not in_self_test:
            print(
                termcolor.colored(
                    "Upozornění: v configu není specifikovaný checker. "
                    "Vygenerované vstupy tudíž nejsou zkontrolované. "
                    "Doporučujeme proto nastavit v sekci [tests] pole `checker`.",
                    color="cyan",
                ),
                file=sys.stderr,
            )
    else:
        checker = Checker(task_config)
        suite.addTest(CheckerDistinguishesSubtasks(task_config, checker, get_subtasks))
        suite.addTest(
            InputsPassChecker(task_config, checker, get_subtasks, in_self_test)
        )
