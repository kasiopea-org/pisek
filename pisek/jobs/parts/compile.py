# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>
# Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import shutil
import subprocess
import sys

from pisek.env.env import Env
from pisek.paths import TaskPath
from pisek.jobs.jobs import State, PipelineItemFailure
from pisek.jobs.parts.program import ProgramsJob


class Compile(ProgramsJob):
    """Job that compiles a program."""

    def __init__(
        self,
        env: Env,
        program: TaskPath,
        use_stub: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(env=env, name=f"Compile {program:n}", **kwargs)
        self.program = program
        self.use_stub = use_stub
        self.target = TaskPath.executable_file(self._env, program.name)

        self.stub = None
        self.headers = []

        if use_stub and self._env.config.stub:
            self.stub = TaskPath(self._env.config.stub)
        if use_stub and self._env.config.headers:
            self.headers = [TaskPath(header) for header in self._env.config.headers]

    def _resolve_extension(self, name: TaskPath) -> TaskPath:
        """
        Given `name`, finds a file named `name`.[ext],
        where [ext] is a file extension for one of the supported languages.

        If a name with a valid extension is given, it is returned unchanged
        """
        extensions = supported_extensions()
        candidates = []
        path = name.path
        for ext in extensions:
            if os.path.isfile(path + ext):
                candidates.append(path + ext)
            if path.endswith(ext) and os.path.isfile(path):
                # Extension already present in `name`
                candidates.append(path)

        if len(candidates) == 0:
            raise PipelineItemFailure(f"No program with given name exists: {path}")
        if len(candidates) > 1:
            raise PipelineItemFailure(
                f"Multiple programs with same name exist: {', '.join(candidates)}"
            )

        return TaskPath.from_abspath(candidates[0])

    def _run(self):
        """Compiles program."""
        program = self._resolve_extension(self.program)
        self.makedirs(TaskPath.executable_path(self._env, "."))

        _, ext = os.path.splitext(program.path)

        if ext in COMPILE_RULES:
            COMPILE_RULES[ext](self, program)
        else:
            raise PipelineItemFailure(f"No rule for compiling {program:p}.")

        self._access_file(program)
        self._access_file(self._load_compiled(self.program))

    def _compile_cpp(self, program: TaskPath):
        cpp_flags = ["-std=c++17", "-O2", "-Wall", "-lm", "-Wshadow", self._c_colors()]

        cpp_flags += self._add_stub("cpp")

        return self._run_compilation(
            ["g++", program.path, "-o", self.target.path] + cpp_flags, program
        )

    def _compile_c(self, program: TaskPath):
        c_flags = ["-std=c17", "-O2", "-Wall", "-lm", "-Wshadow", self._c_colors()]

        c_flags += self._add_stub("c")

        return self._run_compilation(
            ["gcc", program.path, "-o", self.target.path] + c_flags, program
        )

    def _c_colors(self):
        if not self._env.no_colors:
            return "-fdiagnostics-color=always"
        else:
            return "-fdiagnostics-color=never"

    def _compile_pas(self, program: TaskPath):
        build_dir = TaskPath.executable_path(self._env, ".")
        pas_flags = [
            "-gl",
            "-O3",
            "-Sg",
            "-o" + self.target.path,
            "-FE" + build_dir.path,
        ]

        return self._run_compilation(["fpc"] + pas_flags + [program.path], program)

    def _compile_rust(self, program: TaskPath):
        return self._run_compilation(
            ["rustc", "-O", "-o", self.target.path, program.path], program
        )

    def _run_compilation(self, args: list[str], program: TaskPath, **kwargs) -> None:
        self._check_tool(args[0])

        comp = subprocess.Popen(args, **kwargs, stderr=subprocess.PIPE)
        while comp.stderr is not None:
            line = comp.stderr.readline().decode()
            if not line:
                break
            self._print(line, end="", stderr=True)

        comp.wait()
        if comp.returncode != 0:
            raise PipelineItemFailure(f"Compilation of {program:p} failed.")

    def _check_tool(self, tool: str) -> None:
        """Checks that a tool exists."""
        try:
            subprocess.run(
                tool.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=0
            )
        except subprocess.TimeoutExpired:
            pass
        except FileNotFoundError:
            raise PipelineItemFailure(f"Missing tool: {tool}")

    def _compile_script(self, program: TaskPath) -> None:
        if not self.valid_shebang(program):
            raise PipelineItemFailure(
                f"{program} has invalid shebang. "
                "For Python should first line be '#!/usr/bin/env python3' or similar.\n"
                "Check also that you are using linux eol."
            )

        with open(program.path, "r", newline="\n") as f:
            interpreter = f.readline().strip().lstrip("#!")
        self._check_tool(interpreter)

        shutil.copyfile(program.path, self.target.path)
        self._chmod_exec(self.target)

    @staticmethod
    def valid_shebang(program: TaskPath) -> bool:
        """Check if file has shebang and if the shebang is valid"""

        with open(program.path, "r", newline="\n") as f:
            first_line = f.readline()

        if not first_line.startswith("#!"):
            return False

        if first_line.endswith("\r\n"):
            return False

        if os.path.splitext(program.path)[1] == ".py":
            return any(
                first_line == f"#!/usr/bin/env {interpreter}\n"
                for interpreter in VALID_PYTHON_INTERPRETERS
            )
        else:
            # No check performed for non-Python at the moment
            return True

    @staticmethod
    def _chmod_exec(filepath: TaskPath) -> None:
        st = os.stat(filepath.path)
        os.chmod(filepath.path, st.st_mode | 0o111)

    def _add_stub(self, extension):
        flags = []

        if self.stub is not None:
            filename = TaskPath(f"{self.stub:p}.{extension}")
            self._access_file(filename)
            flags += [filename.path]

        for header in self.headers:
            self._access_file(header)
            directory = os.path.normpath(os.path.dirname(header.path))
            flags += [f"-iquote{directory}"]

        return flags


# This is the list of supported Python interpreters.
# Used for checking the shebang.
VALID_PYTHON_INTERPRETERS = ["python3", "pypy3"]

COMPILE_RULES = {
    ".py": Compile._compile_script,
    ".sh": Compile._compile_script,
    ".c": Compile._compile_c,
    ".cc": Compile._compile_cpp,
    ".cpp": Compile._compile_cpp,
    ".pas": Compile._compile_pas,
    ".rs": Compile._compile_rust,
}


def supported_extensions() -> list[str]:
    return list(COMPILE_RULES)
