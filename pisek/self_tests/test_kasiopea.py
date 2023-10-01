"""
A module for testing pisek itself. The strategy is to take a functioning
fixture of a task and then break it in various small ways to see whether
pisek catches the problem.
"""
import unittest
import shutil
import os

from pisek.self_tests.util import TestFixtureVariant, overwrite_file, modify_config


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
        overwrite_file(self.task_dir, "gen.cpp", "gen_2.py", new_file_name="gen.py")


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
        overwrite_file(
            self.task_dir, "solve_0b.py", "solve_4b.cpp", new_file_name="solve_0b.cpp"
        )


class TestJudge(TestSoucetKasiopea):
    def expecting_success(self):
        return True

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["tests"]["out_check"] = "judge"
            raw_config["tests"]["out_judge"] = "judge"

        modify_config(self.task_dir, modification_fn)


class TestPythonJudge(TestSoucetKasiopea):
    def expecting_success(self):
        return True

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["tests"]["out_check"] = "judge"
            raw_config["tests"]["out_judge"] = "judge_py"

        modify_config(self.task_dir, modification_fn)


class TestBadJudge(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["tests"]["out_check"] = "judge"
            raw_config["tests"]["out_judge"] = "judge_bad"

        modify_config(self.task_dir, modification_fn)


class TestBadWhitespaceJudge(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["tests"]["out_check"] = "judge"
            raw_config["tests"]["out_judge"] = "judge_bad_whitespace"

        modify_config(self.task_dir, modification_fn)


class TestPythonCRLF(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def modify_task(self):
        os.remove(os.path.join(self.task_dir, "solve.py"))

        new_program = [
            "#!/usr/bin/env python3",
            "t = int(input())",
            "for i in range(t):",
            "    a, b = [int(x) for x in input().split()]",
            "    c = a + b",
            "    print(c)",
        ]
        with open(os.path.join(self.task_dir, "solve.py"), "w") as f:
            f.write("\r\n".join(new_program))


class TestLooseChecker(TestSoucetKasiopea):
    """A checker that cannot distinguish between subtasks."""

    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "check.py", "check_loose.py")


class TestStrictChecker(TestSoucetKasiopea):
    """A checker whose bounds are stricter than what the generator creates."""

    def expecting_success(self):
        return False

    def modify_task(self):
        overwrite_file(self.task_dir, "check.py", "check_strict.py")

class TestBigInput(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["limits"]["input_max_size"] = "0"

        modify_config(self.task_dir, modification_fn)

class TestBigOutput(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["limits"]["output_max_size"] = "0"

        modify_config(self.task_dir, modification_fn)

class TestExtraConfigKeys(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def catch_exceptions(self):
        return True

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["task"]["foo"] = "bar"

        modify_config(self.task_dir, modification_fn)


class TestExtraConfigKeysInSubtask(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def catch_exceptions(self):
        return True

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config["test01"]["foo"] = "bar"

        modify_config(self.task_dir, modification_fn)


class TestExtraConfigSection(TestSoucetKasiopea):
    def expecting_success(self):
        return False

    def catch_exceptions(self):
        return True

    def modify_task(self):
        def modification_fn(raw_config):
            raw_config.add_section("baz")
            raw_config["baz"]["foo"] = "bar"

        modify_config(self.task_dir, modification_fn)


if __name__ == "__main__":
    unittest.main()
