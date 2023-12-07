# pisek  - Tool for developing tasks for programming competitions.
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

from copy import copy, deepcopy
from typing import Iterator, Callable, MutableSet, Any


class BaseEnv:
    """
    Collection of enviroment variables witch logs whether each variable was accessed.

    Variable can be accessed as such:
        env.variable
    It is then logged as used. Use BaseEnv.get_accessed to get all of them.

    Unset variables cannot be accessed. (That raises an error.)
    Set them to default value instead.
    """

    def __init__(self, **vars) -> None:
        self._vars = vars
        self._log_off = 0
        self._locked = False
        self._accessed: set[str] = set([])

    def __setattr__(self, __name: str, __value: Any) -> None:
        """
        Disallow setting variables as they should be in _vars.
        """
        if __name not in ("_vars", "_log_off", "_locked", "_accessed"):
            raise RuntimeError(
                f"Cannot set attribute '{__name}'. Use 'self[\"{__name}\"] = {__value}' instead."
            )
        super().__setattr__(__name, __value)

    def _get(self, name: str) -> Any:
        """
        Gets variable of given name.
        If name contains a dot it is interpreted as variable of subenv.
        """
        name = name.lstrip(".")
        if name == "":
            return self

        first = name.split(".", 1)[0]
        if (
            self._log_off <= 0 and first in self._vars
        ):  # I don't know how __iter__ can get in here, but apparently
            self._accessed.add(first)

        if "." in name:
            first, rest = name.split(".", 1)
            if first not in self._vars:
                raise KeyError(f"Env has no variable {first}")
            return getattr(self._vars[first], rest)
        else:
            if name not in self._vars:
                raise KeyError(f"Env has no variable {name}")
            return self._vars[name]

    def __contains__(self, name: str):
        """
        Returns whether variable of given name exists.
        If name contains a dot it is interpreted as variable of subenv.
        """
        name = name.lstrip(".")
        if name == "":
            return self

        if "." in name:
            first, rest = name.split(".", 1)
            if first not in self._vars:
                return False
            return rest in self._vars[first]
        else:
            return name in self._vars

    def __getitem__(self, key: str) -> Any:
        """Gets variable with given name and logs access to it."""
        return self._get(str(key))

    def __setitem__(self, key: str, val: Any):
        """Sets variable with given name."""
        self._set(key, val)

    def __getattr__(self, name: str) -> Any:
        """Gets variable with given name and logs access to it."""
        return self._get(name)

    def __len__(self) -> int:
        """Returns number of stared variables."""
        return len(self._vars)

    def keys(self) -> list[str]:
        """
        Return all names of variables stored.
        Logs each variable.
        """
        self._accessed |= self._vars.keys()
        return list(self._vars.keys())

    def items(self) -> list[tuple[str, Any]]:
        """
        Return (name, value) for each variable stored.
        Logs each variable.
        """
        self._accessed |= self._vars.keys()
        return list(self._vars.items())

    def subenvs(self) -> list[tuple[str, Any]]:
        """
        Return (name, value) for each subenv stored.
        Logs each variable.
        """
        return list(filter(lambda v: isinstance(v[1], BaseEnv), self.items()))

    def _set(self, name: str, value: Any):
        """Sets variable to value. Use only in __init__ and for other cases use fork."""
        self._vars[name] = value

    def _set_log(self, val: bool) -> None:
        """Sets logging for this env and all subenvs."""
        if val:
            self._log_off -= 1
        else:
            self._log_off += 1

        for var in self._vars:
            if isinstance(self._vars[var], BaseEnv):
                self._vars[var]._set_log(val)

    @staticmethod
    def log_off(f: Callable[..., Any]) -> Callable[..., Any]:
        """Disables logging for a method."""

        def g(self, *args, **kwargs):
            self._set_log(False)
            result = f(self, *args, **kwargs)
            self._set_log(True)
            return result

        return g

    @log_off
    def get_without_log(self, name: str) -> Any:
        """Gets variable without logging."""
        return self._get(name)

    @log_off
    def fork(self, **kwargs):
        """
        Make copy of this env overriding variables specified in **kwargs.

        Accesses to env's variables (to this point) are logged in forked env as well.
        Subsequent accesses are logged only to respective BaseEnv.
        """
        if self._locked:
            raise RuntimeError("Locked BaseEnv cannot be forked.")

        # XXX: Ok this is nasty
        # We actually need a copied object of the same class to keep methods
        # However we cannot call it's __init__ because we don't want to repeat
        # all calculations. But fortunately we have all stored in _vars.
        instance = self.__class__.__new__(self.__class__)
        BaseEnv.__init__(instance, **{**deepcopy(self._vars), **kwargs})
        assert instance._accessed == set([])
        return instance

    def lock(self) -> "BaseEnv":
        """Lock this BaseEnv and all subenvs so they cannot be forked."""
        self._locked = True
        for var in self._vars:
            if isinstance(self._vars[var], BaseEnv):
                self._vars[var].lock()

        return self

    @log_off
    def get_accessed(self) -> list[str]:
        """Get all accessed variables in thi env and all subenvs."""
        accessed = []
        for name in self._accessed:
            if isinstance(self._vars[name], BaseEnv):
                accessed += list(
                    map(lambda x: f"{name}.{x}", self._vars[name].get_accessed())
                )
            else:
                accessed.append(name)
        return accessed

    def __deepcopy__(self, memo):
        """Deepcopies this env. Clears all logged accesses."""
        copy = self.fork()
        memo[id(self)] = copy
        return copy

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} "
            + ", ".join(
                [
                    f"{name}=<{var.__class__.__name__}>"
                    if isinstance(var, BaseEnv)
                    else f"{name}={var}"
                    for name, var in self._vars.items()
                ]
            )
            + ">"
        )

    __str__ = __repr__


class Env(BaseEnv):
    """Top level BaseEnv"""

    pass
