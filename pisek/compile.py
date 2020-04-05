import subprocess
import os
import shutil
from typing import Dict, List, Optional, Tuple
from . import util


class CompileRules:
    """ Abstract class for compile rules """

    def __init__(self, supported_extensions: List[str]) -> None:
        self.supported = supported_extensions

    def compile(self, filepath: str, dry_run: bool = False) -> Optional[str]:
        """ Takes a `filepath` and either:
        - compiles it and returns the path to the executable (str) or
        - returns None if an error occurred
        If dry_run is True, returns the path to the would-be executable and does nothing.
        """
        raise NotImplementedError

    @staticmethod
    def _chmod_exec(filepath: str) -> None:
        st = os.stat(filepath)
        os.chmod(filepath, st.st_mode | 0o111)


class PythonCompileRules(CompileRules):
    def __init__(self, supported_extensions: List[str]) -> None:
        super().__init__(supported_extensions)

    def compile(self, filepath: str, dry_run: bool = True) -> Optional[str]:
        dirname, filename, _ = _split_path(filepath)
        build_dir = util.get_build_dir(dirname)
        result_filepath = os.path.join(build_dir, filename)
        if dry_run:
            return result_filepath

        if not self.valid_shebang(filepath):
            raise RuntimeError(f"{filename} má neplatný shebang")

        shutil.copyfile(filepath, result_filepath)
        self._chmod_exec(result_filepath)
        return result_filepath

    @staticmethod
    def valid_shebang(filepath: str) -> bool:
        """ Check if file has shebang and if the shebang is valid """

        with open(filepath, "r") as f:
            first_line = f.readline()

        if not first_line.startswith("#!"):
            return False

        # TODO: check if the shebang is proper,
        #       i.e. /usr/bin/env python
        return True


class CPPCompileRules(CompileRules):
    def __init__(self, supported_extensions: List[str]) -> None:
        super().__init__(supported_extensions)

    def compile(self, filepath: str, dry_run: bool = True) -> Optional[str]:
        dirname, filename, _ = _split_path(filepath)
        build_dir = util.get_build_dir(dirname)
        result_filepath = os.path.join(build_dir, filename)
        if dry_run:
            return result_filepath

        cpp_flags = ["-std=c++14", "-O2", "-Wall", "-Wshadow"]
        gpp = subprocess.run(["g++", filepath, "-o", result_filepath] + cpp_flags)
        return result_filepath if gpp.returncode == 0 else None


COMPILE_RULES: List[CompileRules] = [
    PythonCompileRules([".py"]),
    CPPCompileRules([".cpp", ".cc"]),
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


def compile(filepath: str, dry_run: bool = False) -> Optional[str]:
    # asserts that filepath is a valid path

    # make the path absolute
    filepath = os.path.abspath(filepath)
    dirname, _ = os.path.split(filepath)

    path_to_build = util.get_build_dir(dirname)
    if not dry_run:
        os.makedirs(path_to_build, exist_ok=True)

    _, file_extension = os.path.splitext(filepath)

    for compile_rule in COMPILE_RULES:
        if file_extension in compile_rule.supported:
            return compile_rule.compile(filepath, dry_run)

    return None
