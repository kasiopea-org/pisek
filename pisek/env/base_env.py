# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Any, TYPE_CHECKING, Callable

from pisek.env.context import ContextModel


class BaseEnv(ContextModel):
    """
    Collection of environment variables which logs whether each variable was accessed.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._accessed: set[str] = set()
        self._logging: bool = True

        self._direct_subenvs: list[str] = []
        self._dict_subenvs: list[str] = []
        self._precompute_subenvs()

    if not TYPE_CHECKING:
        # XXX: This is a bit black-magicky because of efficiency
        # Be careful when touching this
        def __getattribute__(self, item: str) -> Any:
            if not item.startswith("_") and hasattr(self, "_accessed"):
                super().__getattribute__("_accessed").add(item)
            return ContextModel.__getattribute__(self, item)

    def fork(self):
        """Make copy of this env with no accesses logged."""
        model = self.model_copy(deep=True)
        model.clear_accesses()
        return model

    def _precompute_subenvs(self):
        def is_env(item: Any) -> bool:
            return isinstance(item, BaseEnv)

        for key in self.model_fields:
            item = getattr(self, key)
            if is_env(item):
                self._direct_subenvs.append(key)
            elif isinstance(item, dict) and any(map(is_env, item.values())):
                assert all(map(is_env, item.values()))
                self._dict_subenvs.append(key)

    @staticmethod
    def _recursive_call(
        function: Callable[["BaseEnv"], None],
    ) -> Callable[["BaseEnv"], None]:
        def recursive(self: "BaseEnv") -> None:
            for direct_subenv in self._direct_subenvs:
                recursive(super().__getattribute__(direct_subenv))

            for dict_subenv in self._dict_subenvs:
                subenv = super().__getattribute__(dict_subenv)
                for subitem in subenv.values():
                    recursive(subitem)

            function(self)

        return recursive

    @_recursive_call
    def clear_accesses(self) -> None:
        """Remove all logged accesses."""
        self._accessed.clear()

    def get_accessed(self) -> set[tuple[str, ...]]:
        """Get all accessed field names in this env (and all subenvs)."""
        accessed = set()
        self._accessed &= set(self.model_fields) | set(self.model_computed_fields)
        for key in self._accessed:
            item = getattr(self, key)
            if isinstance(item, BaseEnv):
                accessed |= {(key, *subkey) for subkey in item.get_accessed()}
            elif isinstance(item, dict) and all(
                isinstance(val, BaseEnv) for val in item.values()
            ):
                accessed |= {
                    (key, dict_key, *subkey)
                    for dict_key, subenv in item.items()
                    for subkey in subenv.get_accessed()
                }
            else:
                accessed.add((key,))

        return accessed

    def get_compound(self, key: tuple[str, ...]) -> Any:
        """Get attribute that may be nested deeper and indexed."""
        obj = self
        for key_part in key:
            if isinstance(obj, BaseEnv):
                obj = getattr(obj, key_part)
            elif isinstance(obj, dict):
                obj = obj[type(list(obj.keys())[0])(key_part)]
            else:
                raise ValueError(f"Can't get compound key on type '{type(obj)}'.")
        return obj
