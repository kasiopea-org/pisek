from typing import Dict, Any

class Env:
    def __init__(self, accessed : Dict[str,bool] = {}, **vars) -> None:
        self.vars = vars
        self.accessed = accessed

    def __getattr__(self, name: str) -> Any:
        if name in self.vars:
            self.accessed[name] = True
        return self.vars[name]

    def get_without_log(self, name: str) -> Any:
        if name == "config":
            return ""
        return self.vars[name]

    def fork(self, **args):
        return Env(**{**self.vars, **args})
