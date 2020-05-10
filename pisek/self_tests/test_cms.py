import os
import shutil

import unittest

from pisek.self_tests.util import TestFixtureVariant, overwrite_file
from pisek import util


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
