from copy import copy, deepcopy
from typing import List, Callable, MutableSet, Any

class BaseEnv:
    def __init__(self, accessed : MutableSet[str] = set([]), **vars) -> None:
        self.vars = vars
        self.log_on = True
        self._accessed = copy(accessed)

    def _get(self, name: str) -> Any:
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
        self.vars[name] = value

    def __getattr__(self, name: str) -> Any:
        if self.log_on and \
           name in self.vars and not isinstance(self.vars[name], BaseEnv):
                self._accessed.add(name)
        return self._get(name)

    def _set_log(self, val: bool) -> None:
        self.log_on = val
        for var in self.vars:
            if isinstance(self.vars[var], BaseEnv):
                self.vars[var]._set_log(val)
    
    @staticmethod
    def log_off(f : Callable[...,Any]):
        def g(self, *args, **kwargs):
            self._set_log(False)
            result = f(self, *args, **kwargs)
            self._set_log(True)
            return result
        return g
    
    @log_off    
    def get_without_log(self, name: str) -> Any:
        return self._get(name)

    @log_off
    def fork(self, **args):
        return BaseEnv(**{**deepcopy(self.vars), **args})

    @log_off
    def get_accessed(self) -> List[str]:
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
    pass
