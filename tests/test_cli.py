"""
Tests the command-line interface.
"""

import os

import unittest
from io import StringIO
from unittest import mock

from util import TestFixture

from pisek.__main__ import main
from pisek.utils import util


def quote_test_suite_output(l):
    return util.quote_output("".join([x[1] for x in l]))


class TestCLI(TestFixture):
    def fixture_path(self):
        return "../fixtures/sum_cms/"

    def args(self):
        return [["--timeout", "1"]]

    def runTest(self):
        if not self.fixture_path():
            return

        self.log_files()

        with mock.patch("sys.stdout", new=StringIO()) as std_out:
            with mock.patch("sys.stderr", new=StringIO()) as std_err:
                for args_i in self.args():
                    result = main(args_i)

                    self.assertFalse(
                        result,
                        f"Command failed: {' '.join(args_i)}",
                    )

        self.check_files()


class TestCLITestSolution(TestCLI):
    def args(self):
        return [["test", "solution", "solve"]]


class TestCLITestGenerator(TestCLI):
    def args(self):
        return [["test", "generator"]]


class TestCLIClean(TestCLI):
    def args(self):
        return [["clean"]]


class TestCLITestingLog(TestCLI):
    def args(self):
        return [["--testing-log"]]

    def created_files(self):
        return ["testing_log.json"]


class TestCLIVisualize(TestCLI):
    def args(self):
        return [["--testing-log"], ["visualize"]]

    def created_files(self):
        return ["testing_log.json"]


if __name__ == "__main__":
    unittest.main(verbosity=2)
