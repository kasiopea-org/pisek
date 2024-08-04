import os
import shutil

import unittest

from pisek.utils.paths import GENERATED_SUBDIR
from util import TestFixtureVariant, overwrite_file, modify_config
from pisek.config.task_config import load_config


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
            self.task_dir, task_config.data_subdir.path, GENERATED_SUBDIR
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


class TestStrictChecker(TestSumCMS):
    """A checker whose bounds are stricter than what the generator creates."""

    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "check.py", "check_strict.py")


class TestDirtySample(TestSumCMS):
    """Sample without newline at the end."""

    def expecting_success(self):
        return False

    def modify_task(self):
        with open(os.path.join(self.task_dir, "sample_01.in"), "w") as f:
            f.write("1 2")


class TestNoLFInTextInput(TestSumCMS):
    """Input without newline at the end with in_format=text."""

    def expecting_success(self):
        return False

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["tests"]["in_gen"] = "gen_no_lf"
            raw_config["tests"]["checker"] = ""

        modify_config(self.task_dir, modification_fn)


class TestNoLFInBinaryInput(TestSumCMS):
    """Input without newline at the end with in_format=binary."""

    def expecting_success(self):
        return True

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["tests"]["in_format"] = "binary"
            raw_config["tests"]["in_gen"] = "gen_no_lf"
            raw_config["tests"]["checker"] = ""

        modify_config(self.task_dir, modification_fn)


class TestNoLFInTextOutput(TestSumCMS):
    """Output without newline at the end with out_format=text."""

    def expecting_success(self):
        return False

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["solution_solve"]["source"] = "solve_no_lf"
            raw_config["tests"]["checker"] = ""

        modify_config(self.task_dir, modification_fn)


class TestNoLFInBinaryOutput(TestSumCMS):
    """Output without newline at the end with out_format=binary."""

    def expecting_success(self):
        return True

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["tests"]["out_format"] = "binary"
            raw_config["solution_solve"]["source"] = "solve_no_lf"
            raw_config["tests"]["checker"] = ""

        modify_config(self.task_dir, modification_fn)


class TestGuess(TestFixtureVariant):
    def fixture_path(self):
        return "../fixtures/guess/"


class TestStub(TestFixtureVariant):
    def fixture_path(self):
        return "../fixtures/odd_stub/"


class TestBigInput(TestStub):
    def expecting_success(self):
        return False

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["limits"]["input_max_size"] = "1"

        modify_config(self.task_dir, modification_fn)


class TestBigOutput(TestStub):
    def expecting_success(self):
        return False

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["limits"]["output_max_size"] = "1"

        modify_config(self.task_dir, modification_fn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
