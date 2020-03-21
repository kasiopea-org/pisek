"""
A module for testing pisek itself. The strategy is to take a functioning
fixture of a task and then break it in various small ways to see whether
pisek catches the problem.
"""
import unittest
import shutil
import os

from pisek.self_tests.util import TestFixtureVariant


class TestSoucetKasiopea(TestFixtureVariant):
    def fixture_path(self):
        return "../../fixtures/soucet_kasiopea/"


class TestMissingSampleIn(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "sample.in"))


class TestMissingSampleOut(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "sample.out"))


class TestWrongSampleOut(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def modify_task(self):
        with open(os.path.join(self.task_dir, "sample.out"), "a") as f:
            f.write("0\n")


class TestMissingGenerator(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "gen.cpp"))


class TestBadGenerator(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def modify_task(self):
        generator_filename = os.path.join(self.task_dir, "gen.cpp")
        os.remove(generator_filename)

        with open(generator_filename, "w") as f:
            f.write("int main() { return 0; }\n")


class TestPythonGenerator(TestSoucetKasiopea):
    def expecting_success(self):
        return True

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "gen.cpp"))
        shutil.copy(
            os.path.join(self.task_dir, "gen_2.py"),
            os.path.join(self.task_dir, "gen.py"),
        )


class TestNonHexaPythonGenerator(TestSoucetKasiopea):
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


class TestNonHexaGenerator(TestSoucetKasiopea):
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


class TestScoreCounting(TestSoucetKasiopea):
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
