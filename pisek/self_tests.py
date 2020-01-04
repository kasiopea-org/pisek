"""
A module for testing pisek itself. The strategy is to take a functioning
fixture of a task and then break it in various small ways to see whether
pisek catches the problem.
"""
import unittest
import shutil
import tempfile
import os

import pisek.tests


class TestTask1(unittest.TestCase):
    def setUp(self):
        self.task_dir_orig = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../fixtures/task_1/")
        )
        self.task_dir = tempfile.mkdtemp()

        # shutil.copytree() requires that the destination directory does not exist,
        os.rmdir(self.task_dir)
        shutil.copytree(self.task_dir_orig, self.task_dir)

    def expecting_success(self):
        return True

    def modify_task(self):
        # Code which modifies the task before running the tests should go here.
        # For example, if we want to check that the presence of `sample.in` is
        # correctly checked for, we would remove the file here.
        pass

    def runTest(self):
        self.modify_task()
        suite = pisek.tests.kasiopea_test_suite(self.task_dir)

        with open(os.devnull, "w") as devnull:
            runner = unittest.TextTestRunner(stream=devnull)

            result = runner.run(suite)

        self.assertEqual(
            result.wasSuccessful(),
            self.expecting_success(),
            "Neočekávaný výsledek testu: test {}měl projít, ale {}prošel".format(
                "" if self.expecting_success() else "ne",
                "" if result.wasSuccessful() else "ne",
            ),
        )

    def tearDown(self):
        shutil.rmtree(self.task_dir)


class TestMissingSampleIn(TestTask1):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "sample.in"))


class TestMissingSampleOut(TestTask1):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "sample.out"))


class TestMissingGenerator(TestTask1):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "gen.cpp"))


class TestBadGenerator(TestTask1):
    def expecting_success(self):
        return False

    def modify_task(self):
        generator_filename = os.path.join(self.task_dir, "gen.cpp")
        os.remove(generator_filename)

        with open(generator_filename, "w") as f:
            f.write("int main() { return 0; }\n")


class TestPythonGenerator(TestTask1):
    def expecting_success(self):
        return True

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "gen.cpp"))

        with open(os.path.join(self.task_dir, "gen.py"), "w") as f:
            f.write("#!/usr/bin/env python3\nimport sys\nprint(sys.argv[1])\n")


if __name__ == "__main__":
    unittest.main()
