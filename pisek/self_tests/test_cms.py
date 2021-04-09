import os
import shutil

import unittest

from pisek.self_tests.util import TestFixtureVariant, overwrite_file
from pisek.task_config import TaskConfig


class TestSoucetCMS(TestFixtureVariant):
    def fixture_path(self):
        return "../../fixtures/soucet_cms/"


class TestMissingGenerator(TestSoucetCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "gen.py"))


class TestGeneratorDoesNotCreateTests(TestSoucetCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "gen.py", "gen_dummy.py")


class TestMissingInputFilesForSubtask(TestSoucetCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "gen.py", "gen_incomplete.py")


class TestOldInputsDeleted(TestSoucetCMS):
    """ Do we get rid of out-of-date inputs? """

    def expecting_success(self):
        return False

    def modify_task(self):
        task_config = TaskConfig(self.task_dir)
        self.data_dir = task_config.get_data_dir()

        # We only care about the generation part, so remove solve.py to stop the tests
        # right after the generator finishes.
        os.remove(os.path.join(self.task_dir, "solve.py"))

        os.makedirs(self.data_dir, exist_ok=True)

        with open(os.path.join(self.data_dir, "01_outdated.in"), "w") as f:
            # This old input does not conform to the subtask! Get rid of it.
            f.write("-3 -2\n")

    def check_end_state(self):
        self.assertNotIn("01_outdated.in", os.listdir(self.data_dir))


class TestScoreCounting(TestSoucetCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(
            self.task_dir, "solve_0b.py", "solve_3b.cpp", new_file_name="solve_0b.cpp"
        )


class TestPartialJudge(TestSoucetCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "judge.cpp", "judge_no_partial.cpp")


class TestInvalidJudgeScore(TestSoucetCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "judge.cpp", "judge_invalid_score.cpp")


class TestLooseChecker(TestSoucetCMS):
    """ A checker that cannot distinguish between subtasks. """

    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "check.py", "check_loose.py")


class TestStrictChecker(TestSoucetCMS):
    """ A checker whose bounds are stricter than what the generator creates. """

    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "check.py", "check_strict.py")


class TestGuess(TestFixtureVariant):
    def fixture_path(self):
        return "../../fixtures/guess/"


if __name__ == "__main__":
    unittest.main(verbosity=2)
