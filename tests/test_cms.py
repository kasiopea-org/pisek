import os
import shutil

import unittest

from pisek.paths import GENERATED_SUBDIR
from util import TestFixtureVariant, overwrite_file
from pisek.env.task_config import load_config


class TestSumCMS(TestFixtureVariant):
    def fixture_path(self):
        return "../fixtures/sum_cms/"


class TestMissingGenerator(TestSumCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "gen.py"))


class TestGeneratorDoesNotCreateTests(TestSumCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "gen.py", "gen_dummy.py")


class TestMissingInputFilesForSubtask(TestSumCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "gen.py", "gen_incomplete.py")


class TestOldInputsDeleted(TestSumCMS):
    """Do we get rid of out-of-date inputs?"""

    def expecting_success(self):
        return False

    def modify_task(self):
        task_config = load_config(self.task_dir)
        self.inputs_dir = os.path.join(
            self.task_dir, task_config.data_subdir, GENERATED_SUBDIR
        )

        # We only care about the generation part, so remove solve.py to stop the tests
        # right after the generator finishes.
        os.remove(os.path.join(self.task_dir, "solve.py"))

        os.makedirs(os.path.join(self.inputs_dir), exist_ok=True)

        with open(os.path.join(self.inputs_dir, "01_outdated.in"), "w") as f:
            # This old input does not conform to the subtask! Get rid of it.
            f.write("-3 -2\n")

    def check_end_state(self):
        self.assertNotIn("01_outdated.in", os.listdir(self.inputs_dir))


class TestScoreCounting(TestSumCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(
            self.task_dir, "solve_0b.py", "solve_3b.cpp", new_file_name="solve_0b.cpp"
        )


class TestPartialJudge(TestSumCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "judge.cpp", "judge_no_partial.cpp")


class TestInvalidJudgeScore(TestSumCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "judge.cpp", "judge_invalid_score.cpp")


class TestLooseChecker(TestSumCMS):
    """A checker that cannot distinguish between subtasks."""

    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "check.py", "check_loose.py")


class TestStrictChecker(TestSumCMS):
    """A checker whose bounds are stricter than what the generator creates."""

    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "check.py", "check_strict.py")


class TestDirtySamle(TestSumCMS):
    """Sample without newline at the end."""

    def expecting_success(self):
        return False

    def modify_task(self):
        sample = ["3", "1 2", "-8 5", "0 0"]
        with open(os.path.join(self.task_dir, "sample.in"), "w") as f:
            f.write("\n".join(sample))


class TestGuess(TestFixtureVariant):
    def fixture_path(self):
        return "../fixtures/guess/"


class TestStub(TestFixtureVariant):
    def fixture_path(self):
        return "../fixtures/odd_stub/"


if __name__ == "__main__":
    unittest.main(verbosity=2)
