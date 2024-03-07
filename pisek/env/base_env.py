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

from enum import StrEnum, auto
from pydantic import Field
from typing import Any, TYPE_CHECKING, Callable, TypeVar


from pisek.env.context import ContextModel


T = TypeVar("T")
TFunc = Callable[..., T]


class BaseEnv(ContextModel):
    """
    Collection of environment variables which logs whether each variable was accessed.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._accessed: set[str] = set()
        self._logging: bool = True
        self._locked: bool = False

    if not TYPE_CHECKING:

        def __getattribute__(self, item: str) -> Any:
            """Overloaded __getattribute__ that logs accesses to fields"""
            # Implementing this method is kind of magical and dangerous. Beware!
            if (
                not item.startswith("_")
                and (item != "model_fields" and item != "model_computed_fields")
                and "_accessed" in self.__dict__
                and self._logging
                and (item in self.model_fields or item in self.model_computed_fields)
            ):
                self._accessed.add(item)
            return super().__getattribute__(item)

    def fork(self):
        """Make copy of this env with no accesses logged."""
        if self._locked:
            raise RuntimeError("Locked BaseEnv cannot be forked.")

        model = self.model_copy(deep=True)
        model._clear_accesses()
        return model

    @staticmethod
    def _recursive_call(
        function: Callable[["BaseEnv"], None]
    ) -> Callable[["BaseEnv"], None]:
        def recursive(self: "BaseEnv") -> None:
            self._logging = False
            for key in self.model_fields:
                item = getattr(self, key)
                if isinstance(item, BaseEnv):
                    recursive(item)
                elif isinstance(item, dict):
                    for subitem in item.values():
                        if isinstance(subitem, BaseEnv):
                            recursive(subitem)

            self._logging = True
            function(self)

        return recursive

    @_recursive_call
    def _clear_accesses(self) -> None:
        """Remove all logged accesses."""
        self._accessed = set()

    @_recursive_call
    def lock(self) -> None:
        """Prevent this Env (and subenvs) from being forked."""
        self._locked = True

    def get_accessed(self) -> list[str]:
        """Get all accessed field names in this env (and all subenvs)."""
        accessed = []
        self._logging = False
        for key in self._accessed:
            item = getattr(self, key)
            if isinstance(item, BaseEnv):
                accessed += [(f"{key}.{subkey}") for subkey in item.get_accessed()]
            elif isinstance(item, dict) and all(
                isinstance(val, BaseEnv) for val in item.values()
            ):
                accessed += [
                    (f"{key}[{dict_key}].{subkey}")
                    for dict_key, subenv in item.items()
                    for subkey in subenv.get_accessed()
                ]
            else:
                accessed.append(key)
        self._logging = True

        return accessed

    def get_compound(self, key: str) -> Any:
        """Get attribute that may be nested deeper and indexed."""
        obj = self
        for key_part in key.split("."):
            if "[" in key_part:
                assert key_part[-1] == "]"
                var, index = key_part[:-1].split("[")
                dict_ = getattr(obj, var)
                obj = dict_[type(list(dict_.keys())[0])(index)]
            else:
                obj = getattr(obj, key_part)
        return obj
