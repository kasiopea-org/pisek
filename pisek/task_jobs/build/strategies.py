# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>
# Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from abc import ABC, abstractmethod
import logging
import inspect
import subprocess
import os

from pisek.env.env import Env
from pisek.utils.util import ChangedCWD
from pisek.utils.text import tab
from pisek.jobs.jobs import PipelineItemFailure
from pisek.config.config_types import BuildStrategyName
from pisek.config.task_config import BuildConfig

logger = logging.getLogger(__name__)

ALL_STRATEGIES: dict[BuildStrategyName, type["BuildStrategy"]] = {}


class BuildStrategy(ABC):
    name: BuildStrategyName
    extra_files: list[str] = []

    def __init__(self, build_section: BuildConfig, env: Env, _print) -> None:
        self._build_section = build_section
        self._env = env
        self._print = _print

    def __init_subclass__(cls):
        if not inspect.isabstract(cls):
            ALL_STRATEGIES[cls.name] = cls
        return super().__init_subclass__()

    @classmethod
    @abstractmethod
    def applicable_on_files(cls, files: list[str]) -> bool:
        pass

    @classmethod
    @abstractmethod
    def applicable_on_directory(cls, directory: str) -> bool:
        pass

    @classmethod
    def applicable(cls, build: BuildConfig, sources: list[str]) -> bool:
        directories = any(os.path.isdir(s) for s in sources)
        if not directories:
            return cls.applicable_on_files(sources)
        elif len(sources) == 1:
            return cls.applicable_on_directory(sources[0])
        else:
            assert False, "Mixed files and directories"

    def build(self, directory: str) -> str:
        self.inputs = os.listdir(directory)
        self.target = os.path.basename(self._build_section.program_name)
        with ChangedCWD(directory):
            return self._build()

    @abstractmethod
    def _build(self) -> str:
        pass

    @classmethod
    def _ends_with(cls, source: str, suffixes: list[str]) -> bool:
        return any(source.endswith(suffix) for suffix in suffixes)

    @classmethod
    def _all_end_with(cls, sources: list[str], suffixes: list[str]) -> bool:
        return all(cls._ends_with(source, suffixes) for source in sources)

    def _run_compilation(self, args: list[str], program: str, **kwargs) -> str:
        self._check_tool(args[0])

        logger.debug("Compiling '" + " ".join(args) + "'")
        comp = subprocess.Popen(args, **kwargs, stderr=subprocess.PIPE)
        while comp.stderr is not None:
            line = comp.stderr.readline().decode()
            if not line:
                break
            self._print(line, end="", stderr=True)

        comp.wait()
        if comp.returncode != 0:
            raise PipelineItemFailure(
                f"Compilation of {program} failed.\n"
                + tab(self._env.colored(" ".join(args), "yellow"))
            )
        return self.target

    def _build_script(self, program: str) -> str:
        self._check_shebang(program)
        with open(program, "r", newline="\n") as f:
            interpreter = f.readline().strip().lstrip("#!")
        self._check_tool(interpreter)
        st = os.stat(program)
        os.chmod(program, st.st_mode | 0o111)
        return program

    def _check_shebang(self, program: str) -> None:
        """Check if file has shebang and if the shebang is valid"""
        with open(program, "r", newline="\n") as f:
            first_line = f.readline()

        if not first_line.startswith("#!"):
            raise PipelineItemFailure(f"Missing shebang in {program}")
        if first_line.endswith("\r\n"):
            raise PipelineItemFailure(f"First line ends with '\\r\\n' in {program}")

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


class BuildScript(BuildStrategy):
    @classmethod
    def applicable_on_directory(cls, directory: str) -> bool:
        return False

    def _build(self) -> str:
        assert len(self.inputs) == 1
        return self._build_script(self.inputs[0])


class BuildBinary(BuildStrategy):
    @classmethod
    def applicable_on_directory(cls, directory: str) -> bool:
        return False


class PythonSingleSource(BuildScript):
    name = BuildStrategyName.python

    @classmethod
    def applicable_on_files(cls, files: list[str]) -> bool:
        return len(files) == 1 and files[0].endswith(".py")


class C(BuildBinary):
    name = BuildStrategyName.c
    extra_files: list[str] = ["headers_c", "extra_sources_c"]

    @classmethod
    def applicable_on_files(cls, files: list[str]) -> bool:
        return cls._all_end_with(files, [".h", ".c"])

    def _build(self) -> str:
        c_flags = ["-std=c17", "-O2", "-Wall", "-lm", "-Wshadow"]
        c_flags.append(
            "-fdiagnostics-color=" + ("never" if self._env.no_colors else "always")
        )

        sources = filter(lambda i: i.endswith(".c"), self.inputs)
        return self._run_compilation(
            ["gcc", *sources, "-o", self.target, "-I."]
            + c_flags
            + self._build_section.comp_args,
            self._build_section.program_name,
        )


class Cpp(BuildBinary):
    name = BuildStrategyName.cpp
    extra_files: list[str] = ["headers_cpp", "extra_sources_cpp"]

    @classmethod
    def applicable_on_files(cls, files: list[str]) -> bool:
        return cls._all_end_with(files, [".h", ".hpp", ".cpp", ".cc"])

    def _build(self) -> str:
        cpp_flags = ["-std=c++20", "-O2", "-Wall", "-lm", "-Wshadow"]
        cpp_flags.append(
            "-fdiagnostics-color=" + ("never" if self._env.no_colors else "always")
        )

        sources = filter(lambda i: self._ends_with(i, [".cpp", ".cc"]), self.inputs)
        return self._run_compilation(
            ["g++", *sources, "-o", self.target, "-I."]
            + cpp_flags
            + self._build_section.comp_args,
            self._build_section.program_name,
        )


class Pascal(BuildBinary):
    name = BuildStrategyName.pascal

    @classmethod
    def applicable_on_files(cls, files: list[str]) -> bool:
        return cls._all_end_with(files, [".pas"])

    def _build(self) -> str:
        pas_flags = ["-gl", "-O3", "-Sg", "-o" + self.target, "-FE."]
        return self._run_compilation(
            ["fpc"] + pas_flags + self.inputs + self._build_section.comp_args,
            self._build_section.program_name,
        )


AUTO_STRATEGIES: list[type[BuildStrategy]] = [PythonSingleSource, C, Cpp, Pascal]
