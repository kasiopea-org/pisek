# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from functools import partial
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from pisek.jobs.jobs import State
from pisek.jobs.parts.program import ProgramJob

class Compile(ProgramJob):
    """Job that compiles a program."""
    def _init(self, program: str, use_manager: bool = False, compile_args: Dict = {}) -> None:
        self.use_manager = use_manager
        self._compile_args = compile_args
        self.target = self._executable(os.path.basename(program))

        self.manager = None
        if self.use_manager:
            manager = self._env.config.solution_manager
            if manager:
                self.manager = self._resolve_path(manager)

        super()._init(f"Compile {os.path.basename(program)}", program)

    def _resolve_extension(self, name: str) -> Optional[str]:
        """
        Given `name`, finds a file named `name`.[ext],
        where [ext] is a file extension for one of the supported languages.

        If a name with a valid extension is given, it is returned unchanged
        """
        extensions = supported_extensions()
        candidates = []
        for ext in extensions:
            if os.path.isfile(name + ext):
                candidates.append(name + ext)
            if name.endswith(ext) and os.path.isfile(name):
                # Extension already present in `name`
                candidates.append(name)

        if len(candidates) == 0:
            self._fail(
                f"No file with given name exists: {name}"
            )
            return None
        if len(candidates) > 1:
            self._fail(
                f"Multiple files with same name exist: {', '.join(candidates)}"
            )
            return None
        return candidates[0]

    def _run(self):
        """Compiles program."""
        program = self._resolve_extension(self.program)
        if program is None:
            return None 

        os.makedirs(self._executable("."), exist_ok=True)

        _, ext = os.path.splitext(program)
        
        if ext in COMPILE_RULES:
            COMPILE_RULES[ext](self, program)
        else:
            self._fail(f"No rule for compiling {program}.")

        if self.state == State.failed:
            return None

        if not self._load_compiled():
            return self._fail("No executable after compilation.")

        self._access_file(program)
        self._access_file(self.executable)

    def _compile_cpp(self, program: str):
        cpp_flags = ["-std=c++17", "-O2", "-Wall", "-lm", "-Wshadow", self._c_colors()]

        if self.manager is not None:  # Interactive task
            cpp_flags += self.manager_flags(".cpp")

        return self._run_compilation(
            ["g++", program, "-o", self.target] + cpp_flags,
            program
        )
    
    def _compile_c(self, program: str):
        c_flags = ["-std=c17", "-O2", "-Wall", "-lm", "-Wshadow", self._c_colors()]

        if self.manager is not None:  # Interactive task
            c_flags += self.manager_flags(".c")

        return self._run_compilation(
            ["gcc", program, "-o", self.target] + c_flags,
            program
        )

    def _c_colors(self):
        if not self._env.get_without_log('plain'):
            return "-fdiagnostics-color=always"
        else:
            return "-fdiagnostics-color=never"
    
    def _compile_pas(self, program: str):
        dir = self._get_build_dir()
        pas_flags = ["-gl", "-O3", "-Sg", "-o" + self.target, "-FE" + dir]

        return self._run_compilation(
            ["fpc"] + pas_flags + [program],
            program
        )
    
    def _compile_rust(self, program: str):
        return self._run_compilation(
            ["rustc", "-O", "-o", self.target, program],
            program
        )

    def _run_compilation(self, args, program, **kwargs):
        try:
            subprocess.run(args[0], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError:
            return self._fail(f"Missing tool: {args[0]}")

        comp = subprocess.Popen(args, **kwargs, stderr=subprocess.PIPE)
        while True:
            line = comp.stderr.readline().decode()
            if not line:
                break
            print(line, end="", file=sys.stderr)
            self.dirty = True

        comp.wait()
        if comp.returncode != 0:
            return self._fail(f"Compilation of {program} failed.")
    
    def _compile_script(self, program: str):
        if not self.valid_shebang(program):
            return self._fail(
                f"{program} has invalid shebang. "
                "For Python should first line be '#!/usr/bin/env python3' or similar.\n"
                "Check also that you are using linux eol."
            )
        
        shutil.copyfile(program, self.target)
        self._chmod_exec(self.target)
        return None
 
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

    @staticmethod
    def _chmod_exec(filepath: str) -> None:
        st = os.stat(filepath)
        os.chmod(filepath, st.st_mode | 0o111)

    def manager_flags(self, extension):
        # For interactive tasks - compile with the manager and add its directory
        # to the search path to allow `#include "manager.h"`
        res = []
        if os.path.dirname(self.manager):
            res.append(f"-I{os.path.dirname(self.manager)}")
        res.append(self.manager + extension)
        
        self._access_file(self.manager + extension)
        
        return res


# This is the list of supported Python interpreters.
# Used for checking the shebang.
VALID_PYTHON_INTERPRETERS = ["python3", "pypy3"]

COMPILE_RULES = {
    '.py': Compile._compile_script,
    '.sh': Compile._compile_script,
    '.c': Compile._compile_c,
    '.cc': Compile._compile_cpp,
    '.cpp': Compile._compile_cpp,
    '.pas': Compile._compile_pas,
    '.rs': Compile._compile_rust,
}


def supported_extensions() -> List[str]:
    return list(COMPILE_RULES)
