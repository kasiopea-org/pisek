from copy import copy, deepcopy
from typing import Iterator, Callable, MutableSet, Any

class BaseEnv:
    """Collection of enviroment variables witch logs whether each variable was accessed."""
    def __init__(self, accessed : MutableSet[str] = set([]), **vars) -> None:
        self._vars = vars
        self._log_off = 0
        self._reserved = False
        self._accessed = copy(accessed)

    def _get(self, name: str) -> Any:
        """
        Gets variable of given name.
        If name contains a dot it is interpreted as variable of subenv.
        """
        name = name.lstrip(".")
        if name == "":
            return self

        first = name.split(".", 1)[0]
        if self._log_off <= 0 and first in self._vars:  # I don't know how __iter__ can get in here, but apparently
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
            return (rest in self._vars[first])
        else:
            return name in self._vars

    def __getitem__(self, key: str) -> Any:
        return self._get(str(key))
 
    def __getattr__(self, name: str) -> Any:
        """Gets variable with given name and logs access to it."""
        return self._get(name)

    def keys(self) -> list[str]:
        return sorted(self._vars.keys())

    def items(self) -> list[tuple[str,Any]]:
        self._accessed |= self._vars.keys()
        return list(sorted(self._vars.items()))

    def iterate(self, name: str, env = None):
        """
        Iterate through vars of (sub)env with given name.
        Each iterations get its own forked env witch accessed only current variable.
        """
        for var in self._get(name).keys():
            fork = env.fork()
            yield (var, getattr(fork, f"{name}.{var}"), fork)

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
    def log_off(f : Callable[...,Any]) -> Callable[...,Any]:
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
        """Make copy of this env overriding variables specified in **kwargs."""
        return self.__class__(accessed=self._accessed, **{**deepcopy(self._vars), **kwargs})

    def reserve(self) -> 'BaseEnv':
        if self._reserved:
            raise RuntimeError("Env is reserved already.")
        else:
            self._reserved = True
            return self

    @log_off
    def get_accessed(self) -> list[str]:
        """Get all accessed variables in thi env and all subenvs."""
        accessed = []
        for name in self._accessed:
            if isinstance(self._vars[name], BaseEnv):
                accessed += list(map(
                    lambda x: f"{name}.{x}",
                    self._vars[name].get_accessed()
                ))
            else:
                accessed.append(name)
        return accessed

    def __deepcopy__(self, memo):
        copy = self.fork()
        memo[id(self)] = copy
        return copy

    def __repr__(self):
        return (f"<{self.__class__.__name__} " +
            ", ".join([f"{name}=<{var.__class__.__name__}>" if isinstance(var, BaseEnv) else f"{name}={var}"
                for name, var in self._vars.items()]) +
        ">")

    __str__ = __repr__

class Env(BaseEnv):
    """Top level BaseEnv"""
    pass
