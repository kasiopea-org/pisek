import subprocess
import os
import shutil
from typing import Dict, List, Optional


class CompileRules:
    """ Abstract class for compile rules """

    def __init__(self, supported_extensions: List[str]) -> None:
        self.supported = supported_extensions

    def compile(self, filename: str, file_extension: str) -> Optional[str]:
        """ Takes a `filename` and a `file_extension` and either
        returns the path to the executable or None when an error occurred
        """
        raise NotImplementedError

    def _chmod_exec(self, filename: str) -> None:
        st = os.stat(filename)
        os.chmod(filename, st.st_mode | 0o111)


class PythonCompileRules(CompileRules):
    def __init__(self, supported_extensions: List[str]) -> None:
        super().__init__(supported_extensions)

    def compile(self, filename: str, file_extension: str) -> Optional[str]:
        result_filename = f"build/{filename}"
        if not self.valid_shebang(f"{filename}{file_extension}"):
            print(f"{filename} has an invalid shebang!")
            return None

        # TODO: raise an exception
        shutil.copyfile(f"{filename}{file_extension}", result_filename)
        self._chmod_exec(result_filename)
        return result_filename

    def valid_shebang(self, filepath: str) -> bool:
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

    def compile(self, filename: str, file_extension: str) -> Optional[str]:
        result_filename = f"build/{filename}"
        cpp_flags = ["-std=c++14", "-O2", "-Wall", "-Wshadow"]
        gpp = subprocess.run(
            ["g++", f"{filename}{file_extension}", "-o", result_filename] + cpp_flags
        )
        return result_filename if gpp.returncode == 0 else None


COMPILE_RULES: List[CompileRules] = [
    PythonCompileRules([".py"]),
    CPPCompileRules([".cpp", ".cc"]),
]


def compile(filepath: str) -> Optional[str]:
    # asserts that filepath is a valid path

    if not os.path.exists("build"):
        os.mkdir("build")

    filename, file_extension = os.path.splitext(filepath)

    for compile_rule in COMPILE_RULES:
        if file_extension in compile_rule.supported:
            return compile_rule.compile(filename, file_extension)

    return None
