from copy import copy, deepcopy
from typing import List, Callable, MutableSet, Any

class BaseEnv:
    """Collection of enviroment variables witch logs whether each variable was accessed."""
    def __init__(self, accessed : MutableSet[str] = set([]), **vars) -> None:
        self.vars = vars
        self.log_on = True
        self.reserved = False
        self._accessed = copy(accessed)

    def _get(self, name: str) -> Any:
        """Gets variable of given name. If name contains a dot it is interpreted as variable of subenv."""
        if "." in name:
            first, rest = name.split(".", 1)
            if first not in self.vars:
                raise KeyError(f"Env has no variable {first}")
            return getattr(self.vars[first], rest) 
        else:
            if name not in self.vars:
                raise KeyError(f"Env has no variable {name}")
            return self.vars[name]
    
    def _set(self, name: str, value: Any):
        """Sets variable to value. Use only in __init__ and for other cases use fork."""
        self.vars[name] = value

    def __getattr__(self, name: str) -> Any:
        """Gets variable with given name and logs access to it."""
        if self.log_on and name in self.vars:
                self._accessed.add(name)
        return self._get(name)

    def _set_log(self, val: bool) -> None:
        """Sets logging for this env and all subenvs."""
        self.log_on = val
        for var in self.vars:
            if isinstance(self.vars[var], BaseEnv):
                self.vars[var]._set_log(val)
    
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
        cls = self.__class__
        forked = cls.__new__(cls)
        BaseEnv.__init__(forked, **{**deepcopy(self.vars), **kwargs}, accessed=self._accessed)
        return forked
    
    def reserve(self) -> None:
        if self.reserved:
            raise RuntimeError("Env is reserved already.")
        else:
            self.reserved = True
            return self

    @log_off
    def get_accessed(self) -> List[str]:
        """Get all accessed variables in thi env and all subenvs."""
        accessed = []
        for name in self._accessed:
            if isinstance(self.vars[name], BaseEnv):
                accessed += list(map(
                    lambda x: f"{name}.{x}",
                    self.vars[name].get_accessed()
                ))
            else:
                accessed.append(name)
        return accessed

    def __deepcopy__(self, memo):
        copy = self.fork()
        memo[id(copy)] = copy
        return copy

class Env(BaseEnv):
    """Top level BaseEnv"""
    pass
