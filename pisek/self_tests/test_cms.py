import os

import unittest

from pisek.self_tests.util import TestFixtureVariant


class TestSoucetCMS(TestFixtureVariant):
    def fixture_path(self):
        return "../../fixtures/soucet_cms/"


class TestMissingGenerator(TestSoucetCMS):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "gen.py"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
