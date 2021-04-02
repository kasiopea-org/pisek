import itertools
import os
import sys
import unittest
import shutil
from typing import List, Tuple, Optional, Callable, Dict

from ..program import RunResult
from ..task_config import TaskConfig
from ..solution import Solution
from ..judge import make_judge, Judge, Verdict
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
        self.solution = Solution(task_config.task_dir, solution_name)


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
            "Ve složce s úlohou nejsou žádné samply "
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


class Subtask:
    def __init__(self, score: int, inputs: List[str], name: Optional[str] = None):
        self.score = score
        # `inputs` is a list of filenames in the data dir.
        self.inputs = inputs
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
    ):
        super().__init__(task_config, solution_name)
        self.run_config = {"timeout": timeout}
        self.judge: Judge = make_judge(self.task_config)
        self.in_self_test = in_self_test

        # Subtasks might not be available when this test case is created, so we need to
        # pass a function to get them later
        self.get_subtasks = get_subtasks

        self.results_cache: Dict[str, Tuple[float, Verdict]] = {}

    def test_passes_samples(self):
        samples_dir = self.task_config.get_samples_dir()
        data_dir = self.task_config.get_data_dir()

        inputs = []
        outputs = []

        for sample_in, sample_out in util.get_samples(samples_dir):
            data_sample_in = os.path.join(data_dir, os.path.basename(sample_in))
            data_sample_out = os.path.join(data_dir, os.path.basename(sample_out))
            # Copy the samples into the data (tests) directory for consistency
            # with the other tests
            shutil.copy(sample_in, data_sample_in)
            shutil.copy(sample_out, data_sample_out)

            inputs.append(os.path.basename(sample_in))
            outputs.append(os.path.basename(sample_out))

        score, message = self.get_score_for_inputs(inputs, outputs)

        self.assertEqual(
            score,
            1,
            f"Řešení {self.solution.name} nefunguje na samplu/samplech."
            f"\n{message or ''}",
        )

    def create_wrong_answer_message(self, input_filename, model_output_filename):
        output_filename = util.get_output_name(
            input_filename, solution_name=self.solution.name
        )
        data_dir = self.task_config.get_data_dir()

        diff = util.diff_files(
            os.path.join(data_dir, model_output_filename),
            os.path.join(data_dir, output_filename),
            "správné řešení",
            f"řešení solveru '{self.solution.name}'",
        )
        # Truncate diff -- we don't want this to be too long
        diff = "".join(itertools.islice(diff, 0, 25))

        return (
            f"Špatná odpověď pro {input_filename}. " f"Diff:\n{util.quote_output(diff)}"
        )

    def get_score_for_inputs(
        self, inputs: List[str], model_outputs: Optional[List[str]] = None
    ) -> Tuple[float, Optional[str]]:
        """
        Runs the solution on the file names (relative to the daa dir)
        listed in `inputs`.
        If `model_outputs` is given, assumes the answers are given in the file names
        listed. Otherwise, uses the model solution's answers.

        Returns a tuple of (score, message), where:

        - score is the minimum score awarded by the judge for these inputs.
          The judge score is in [0.0, 1.0] (possibly non-integral for CMS).

        - message contains information about what, if anything, went wrong
        """
        data_dir = self.task_config.get_data_dir()
        model_solution_name = self.task_config.solutions[0]

        judge_score = 1.0
        messages = []

        if not model_outputs:
            model_outputs = [
                util.get_output_name(inp, solution_name=model_solution_name)
                for inp in inputs
            ]
        else:
            assert len(model_outputs) == len(inputs)

        for input_filename, model_output_filename in zip(inputs, model_outputs):
            if input_filename in self.results_cache:
                from_cache = True
                pts, verdict = self.results_cache[input_filename]
            else:
                from_cache = False
                pts, verdict = self.judge.evaluate(
                    self.solution,
                    input_file=os.path.join(data_dir, input_filename),
                    correct_output=os.path.join(data_dir, model_output_filename),
                    run_config=self.run_config,
                )
                self.results_cache[input_filename] = pts, verdict

            if verdict.result == RunResult.OK:
                c = "·" if pts == 1 else "W" if pts == 0 else "P"

                if pts != 1 and not from_cache:
                    msg = self.create_wrong_answer_message(
                        input_filename, model_output_filename
                    )
                    messages.append(msg)
            else:
                result_chars = {
                    RunResult.TIMEOUT: "T",
                    RunResult.NONZERO_EXIT_CODE: "!",
                }

                c = result_chars[verdict.result]

            self.log(c, end="")

            judge_score = min(judge_score, pts)

            if judge_score == 0:
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
        score = round(score)

        message = "\n".join(messages)
        self.assertEqual(
            score,
            expected_score,
            f"Řešení {self.solution.name} mělo získat {expected_score}b,"
            f" ale získalo {score}b.\n{message}",
        )

    def __str__(self):
        return "Řešení {} získá {}b".format(
            self.solution.name,
            util.get_expected_score(self.solution.name, self.task_config),
        )

    def log(self, msg, *args, **kwargs):
        if not self.in_self_test:
            super().log(msg, *args, **kwargs)
