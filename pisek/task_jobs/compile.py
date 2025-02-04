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
from pisek.utils.paths import TaskPath
from pisek.jobs.jobs import PipelineItemFailure
from pisek.task_jobs.program import ProgramsJob


class Compile(ProgramsJob):
    """Job that compiles a program."""

    def __init__(
        self,
        env: Env,
        program: TaskPath,
        use_stub: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(env=env, name=f"Compile {program:p}", **kwargs)
        self.program = program
        self.use_stub = use_stub
        self.target = TaskPath.executable_file(self._env, program.path)

        self.stub = None
        self.headers = []

        if use_stub:
            self.stub = self._env.config.stub
            self.headers = self._env.config.headers

    def _resolve_extension(self, name: TaskPath) -> tuple[TaskPath, str]:
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
                candidates.append((path + ext, ext))
            if path.endswith(ext) and os.path.isfile(path):
                # Extension already present in `name`
                candidates.append((path, ext))

        if len(candidates) == 0:
            raise PipelineItemFailure(f"No program with given name exists: {path}")
        if len(candidates) > 1:
            raise PipelineItemFailure(
                f"Multiple programs with same name exist: {', '.join(c[0] for c in candidates)}"
            )

        return TaskPath.from_abspath(candidates[0][0]), candidates[0][1]

    def _resolve_manifest(self, dir: TaskPath) -> str:
        """
        Searches the specified directory for a manifest file of one of the supported build systems.
        """
        candidates = []

        for manifest in supported_manifests():
            if os.path.isfile(os.path.join(dir.path, manifest)):
                candidates.append(manifest)

        if len(candidates) == 0:
            raise PipelineItemFailure(
                f"There is no manifest in the given directory: {dir:p}"
            )
        if len(candidates) > 1:
            raise PipelineItemFailure(
                f"There are multiple manifests in {dir:p}: {', '.join(candidates)}"
            )

        return candidates[0]

    def _run(self):
        """Compiles program."""
        self.makedirs(TaskPath.executable_path(self._env, "."))
        compile = None

        if os.path.isdir(self.program.path):
            manifest = self._resolve_manifest(self.program)
            program = self.program

            if manifest in COMPILE_RULES_BY_MANIFEST_FILE:
                compile = COMPILE_RULES_BY_MANIFEST_FILE[manifest]

        if compile is None:
            program, ext = self._resolve_extension(self.program)

            if ext in COMPILE_RULES_BY_EXTENSION:
                compile = COMPILE_RULES_BY_EXTENSION[ext]

        if compile is None:
            raise PipelineItemFailure(f"No rule for compiling {program:p}.")

        compile(self, program)

        self._access_file(program)
        self._access_file(self._load_compiled(self.program))

    def _compile_cpp(self, program: TaskPath):
        cpp_flags = ["-std=c++20", "-O2", "-Wall", "-lm", "-Wshadow", self._c_colors()]

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
        self._run_compilation(
            ["rustc", "-O", "-o", self.target.path, program.path], program
        )

    def _compile_cargo(self, dir: TaskPath):
        target_dir = TaskPath.executable_path(
            self._env, f"{self.target:n}.target/"
        ).path

        self._run_compilation(
            [
                "cargo",
                "build",
                "--quiet",
                "--release",
                "--manifest-path",
                os.path.join(dir.path, "Cargo.toml"),
                "--target-dir",
                target_dir,
            ],
            dir,
        )

        shutil.copyfile(
            os.path.join(target_dir, "release", self.target.name),
            self.target.path,
        )

        self._chmod_exec(self.target)

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
        self.check_shebang(program)

        with open(program.path, "r", newline="\n") as f:
            interpreter = f.readline().strip().lstrip("#!")
        self._check_tool(interpreter)

        shutil.copyfile(program.path, self.target.path)
        self._chmod_exec(self.target)

    def check_shebang(self, program: TaskPath) -> None:
        """Check if file has shebang and if the shebang is valid"""
        with self._open_file(program, "r", newline="\n") as f:
            first_line = f.readline()

        if not first_line.startswith("#!"):
            raise PipelineItemFailure(f"Missing shebang in {program:p}")
        if first_line.endswith("\r\n"):
            raise PipelineItemFailure(f"First line ends with '\\r\\n' in {program:p}")

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

COMPILE_RULES_BY_EXTENSION = {
    ".py": Compile._compile_script,
    ".sh": Compile._compile_script,
    ".c": Compile._compile_c,
    ".cc": Compile._compile_cpp,
    ".cpp": Compile._compile_cpp,
    ".pas": Compile._compile_pas,
    ".rs": Compile._compile_rust,
}

COMPILE_RULES_BY_MANIFEST_FILE = {
    "Cargo.toml": Compile._compile_cargo,
}


def supported_extensions() -> list[str]:
    return list(COMPILE_RULES_BY_EXTENSION)


def supported_manifests() -> list[str]:
    return list(COMPILE_RULES_BY_MANIFEST_FILE)
