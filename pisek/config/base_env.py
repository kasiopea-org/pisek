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

from enum import StrEnum, auto
from pydantic import Field
from typing import Any, TYPE_CHECKING, Optional

from pisek.config.context import ContextModel


class TestingTarget(StrEnum):
    all = auto()
    generator = auto()
    solution = auto()


class BaseEnv(ContextModel):
    """
    Collection of enviroment variables which logs whether each variable was accessed.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._accessed: set[str] = set([])
        self._locked: bool = False

    if not TYPE_CHECKING:

        def __getattribute__(self, item: str) -> Any:
            # Implementing this method is kind of magical and dangerous. Beware!
            if not item.startswith("_") and item != "model_fields":
                if "_accessed" in self.__dict__ and item in self.model_fields:
                    self._accessed.add(item)
            return super().__getattribute__(item)

    def fork(self):
        """
        Make copy of this env overriding variables specified in **kwargs.

        Accesses to env's variables (to this point) are logged in forked env as well.
        Subsequent accesses are logged only to respective BaseEnv.
        """
        if self._locked:
            raise RuntimeError("Locked BaseEnv cannot be forked.")

        model = self.model_copy(deep=True)
        model._clear_accesses()
        return model

    def _clear_accesses(self):
        """Removes all logged accesses."""
        self._accessed = set([])
        for key in self.model_fields:
            item = getattr(self, key)
            if isinstance(item, BaseEnv):
                item._clear_accesses()

    def lock(self) -> "BaseEnv":
        """Lock this BaseEnv and all subenvs so they cannot be forked."""
        self._locked = True
        for key in self.model_fields:
            item = getattr(self, key)
            if isinstance(item, BaseEnv):
                item.lock()

        return self

    def get_accessed(self) -> list[tuple[str, Any]]:
        """Get all accessed variables in this env and all subenvs with their values."""
        accessed = []
        for key in self._accessed:
            item = getattr(self, key)
            if isinstance(item, BaseEnv):
                accessed += [
                    (f"{key}.{subkey}", val) for subkey, val in item.get_accessed()
                ]
            else:
                accessed.append((key, item))

        return accessed
