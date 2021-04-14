"""
Tests the command-line interface.
"""

import os

import unittest
from io import StringIO
from unittest import mock

from pisek.self_tests.util import TestFixture

from pisek.__main__ import main
from pisek import util


def quote_test_suite_output(l):
    return util.quote_output("".join([x[1] for x in l]))


class TestCLI(TestFixture):
    def fixture_path(self):
        return "../../fixtures/soucet_cms/"

    def args(self):
        return ["--timeout", "1"]

    def runTest(self):
        if not self.fixture_path():
            return

        with mock.patch("sys.stdout", new=StringIO()) as std_out:
            with mock.patch("sys.stderr", new=StringIO()) as std_err:
                result = main(self.args())

                if result is not None:
                    self.assertFalse(
                        result.errors,
                        f"Vyskytly se chyby: {quote_test_suite_output(result.errors)}",
                    )
                    self.assertFalse(
                        result.failures,
                        f"Některé testy neseběhly:\n{quote_test_suite_output(result.failures)}",
                    )


class TestCLITestSolution(TestCLI):
    def args(self):
        return ["test", "solution", "solve"]


class TestCLITestGenerator(TestCLI):
    def args(self):
        return ["test", "generator"]


class TestCLIRun(TestCLI):
    def args(self):
        return ["run", "gen", "data"]


class TestCLIClean(TestCLI):
    def args(self):
        return ["clean"]


if __name__ == "__main__":
    unittest.main(verbosity=2)
