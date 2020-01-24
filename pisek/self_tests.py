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
        # We lower the timeout to make the self-tests run faster. The solutions
        # run instantly, with the exception of `solve_slow_4b`, which takes 10 seconds
        # and we want to consider it a timeout
        suite = pisek.tests.kasiopea_test_suite(self.task_dir, timeout=1)

        with open(os.devnull, "w") as devnull:
            runner = unittest.TextTestRunner(stream=devnull, failfast=True)

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


class TestWrongSampleOut(TestTask1):
    def expecting_success(self):
        return False

    def modify_task(self):
        with open(os.path.join(self.task_dir, "sample.out"), "a") as f:
            f.write("0\n")


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
        shutil.copy(
            os.path.join(self.task_dir, "gen_2.py"),
            os.path.join(self.task_dir, "gen.py"),
        )


class TestNonHexaPythonGenerator(TestTask1):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "gen.cpp"))

        new_program = [
            "#!/usr/bin/env python3",
            "import sys",
            "print(sys.argv[1])",
            "print(int(sys.argv[2], 10))",
        ]
        with open(os.path.join(self.task_dir, "gen.py"), "w") as f:
            f.write("\n".join(new_program))


class TestNonHexaGenerator(TestTask1):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "gen.cpp"))

        new_program = [
            "#include <iostream>",
            "#include <string>",
            "int main(int argc, char* argv[]) {",
            "if (argc != 3) { return 1; }",
            "std::cout << argv[1] << std::endl;"
            "std::cout << std::strtoull(argv[2], NULL, 10) << std::endl;"
            "return 0;}",
        ]
        with open(os.path.join(self.task_dir, "gen.cpp"), "w") as f:
            f.write("\n".join(new_program))


class TestScoreCounting(TestTask1):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "solve_0b.py"))
        shutil.copy(
            os.path.join(self.task_dir, "solve_4b.cpp"),
            os.path.join(self.task_dir, "solve_0b.cpp"),
        )


if __name__ == "__main__":
    unittest.main()
