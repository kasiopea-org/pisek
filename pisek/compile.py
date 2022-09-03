import subprocess
import os
import shutil
from typing import Dict, List, Optional, Tuple
from . import util


class CompileRules:
    """Abstract class for compile rules"""

    def __init__(self, supported_extensions: List[str]) -> None:
        self.supported = supported_extensions

    def compile(
        self, filepath: str, build_dir: str = None, dry_run: bool = False, **kwargs
    ) -> Optional[str]:
        """Takes a `filepath` and either:
        - compiles it and returns the path to the executable (str) or
        - returns None if an error occurred
        If dry_run is True, returns the path to the would-be executable and does nothing.
        """
        raise NotImplementedError

    @staticmethod
    def _chmod_exec(filepath: str) -> None:
        st = os.stat(filepath)
        os.chmod(filepath, st.st_mode | 0o111)


# This is the list of supported Python interpreters.
# Used for checking the shebang.
VALID_PYTHON_INTERPRETERS = ["python3", "pypy3"]


class ScriptCompileRules(CompileRules):
    """
    For e.g. Python or Bash, languages whose source code can be directly executed
    when an appropriate shebang is present
    """

    def __init__(self, supported_extensions: List[str]) -> None:
        super().__init__(supported_extensions)

    def compile(
        self, filepath: str, build_dir: str = None, dry_run: bool = True, **kwargs
    ) -> Optional[str]:
        dirname, filename, _ = _split_path(filepath)
        build_dir = build_dir or util.get_build_dir(dirname)
        result_filepath = os.path.join(build_dir, filename)
        if dry_run:
            return result_filepath

        if not self.valid_shebang(filepath):
            raise RuntimeError(
                f"{filename} má neplatný shebang. "
                "Pro Python by měl první řádek být pravděpodobně '#!/usr/bin/env python3' či ekvivalent. "
                " Zkontroluj taky, že soubor používá linuxové konce řádků."
            )

        shutil.copyfile(filepath, result_filepath)
        self._chmod_exec(result_filepath)
        return result_filepath

    @staticmethod
    def valid_shebang(filepath: str) -> bool:
        """Check if file has shebang and if the shebang is valid"""

        with open(filepath, "r", newline="\n") as f:
            first_line = f.readline()

        if not first_line.startswith("#!"):
            return False

        if first_line.endswith("\r\n"):
            return False

        if os.path.splitext(filepath)[1] == ".py":
            return any(
                first_line == f"#!/usr/bin/env {interpreter}\n"
                for interpreter in VALID_PYTHON_INTERPRETERS
            )
        else:
            # No check performed for non-Python at the moment
            return True


def manager_flags(dir, manager, extension):
    # For interactive tasks - compile with the manager and add its directory
    # to the search path to allow `#include "manager.h"`
    res = []
    if os.path.dirname(manager):
        res.append(f"-I{os.path.dirname(manager)}")
    res.append(manager + extension)

    return res


class CPPCompileRules(CompileRules):
    def __init__(self, supported_extensions: List[str]) -> None:
        super().__init__(supported_extensions)

    def compile(
        self,
        filepath: str,
        build_dir: str = None,
        dry_run: bool = True,
        manager=None,
        **kwargs,
    ) -> Optional[str]:
        dirname, filename, _ = _split_path(filepath)
        build_dir = build_dir or util.get_build_dir(dirname)
        result_filepath = os.path.join(build_dir, filename)
        if dry_run:
            return result_filepath

        cpp_flags = ["-std=c++17", "-O2", "-Wall", "-lm", "-Wshadow"]

        if manager is not None:  # Interactive task
            cpp_flags += manager_flags(dirname, manager, ".cpp")

        gpp = subprocess.run(["g++", filepath, "-o", result_filepath] + cpp_flags)
        return result_filepath if gpp.returncode == 0 else None


class CCompileRules(CompileRules):
    def __init__(self, supported_extensions: List[str]) -> None:
        super().__init__(supported_extensions)

    def compile(
        self,
        filepath: str,
        build_dir: str = None,
        dry_run: bool = True,
        manager=None,
        **kwargs,
    ) -> Optional[str]:
        dirname, filename, _ = _split_path(filepath)
        build_dir = build_dir or util.get_build_dir(dirname)
        result_filepath = os.path.join(build_dir, filename)
        if dry_run:
            return result_filepath

        c_flags = ["-std=c17", "-O2", "-Wall", "-lm", "-Wshadow"]

        if manager is not None:  # Interactive task
            c_flags += manager_flags(dirname, manager, ".c")

        gcc = subprocess.run(["gcc", filepath, "-o", result_filepath] + c_flags)
        return result_filepath if gcc.returncode == 0 else None


class PascalCompileRules(CompileRules):
    def __init__(self, supported_extensions: List[str]) -> None:
        super().__init__(supported_extensions)

    def compile(
        self, filepath: str, build_dir: str = None, dry_run: bool = True, **kwargs
    ) -> Optional[str]:
        dirname, filename, _ = _split_path(filepath)
        build_dir = build_dir or util.get_build_dir(dirname)
        result_filepath = os.path.join(build_dir, filename)
        if dry_run:
            return result_filepath

        pas_flags = ["-gl", "-O3", "-Sg", "-FE" + build_dir]
        fpc = subprocess.run(["fpc"] + pas_flags + [filepath])
        return result_filepath if fpc.returncode == 0 else None


COMPILE_RULES: List[CompileRules] = [
    ScriptCompileRules([".py", ".sh"]),
    CPPCompileRules([".cpp", ".cc"]),
    CCompileRules([".c"]),
    PascalCompileRules([".pas"]),
]


def supported_extensions() -> List[str]:
    result: List[str] = []

    for rule in COMPILE_RULES:
        result += rule.supported

    return result


def _split_path(filepath: str) -> Tuple[str, str, str]:
    """
    /path/to/file.ext ~~> (/path/to, file, ext)
    """
    dirname, basename = os.path.split(filepath)
    filename, file_extension = os.path.splitext(basename)
    return dirname, filename, file_extension


def compile(
    filepath: str,
    build_dir: str = None,
    dry_run: bool = False,
    compiler_args: Optional[Dict] = None,
) -> Optional[str]:
    if compiler_args is None:
        compiler_args = {}

    # make the path absolute
    filepath = os.path.abspath(filepath)
    dirname, _ = os.path.split(filepath)

    path_to_build = build_dir or util.get_build_dir(dirname)

    if not dry_run:
        os.makedirs(path_to_build, exist_ok=True)

    _, file_extension = os.path.splitext(filepath)

    for compile_rule in COMPILE_RULES:
        if file_extension in compile_rule.supported:
            return compile_rule.compile(filepath, build_dir, dry_run, **compiler_args)

    return None
