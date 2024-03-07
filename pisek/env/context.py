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

from contextlib import contextmanager
from contextvars import ContextVar
from pydantic import BaseModel

from typing import Any, Iterator


_init_context_var: ContextVar[dict[str, Any]] = ContextVar(
    "_init_context_var", default={}
)


@contextmanager
def init_context(value: dict[str, Any]) -> Iterator[None]:
    token = _init_context_var.set(value)
    try:
        yield
    finally:
        _init_context_var.reset(token)


class ContextModel(BaseModel):
    """Model that adds context when validating at model initialization."""

    def __init__(self, /, **data: Any) -> None:
        __tracebackhide__ = True
        self.__pydantic_validator__.validate_python(
            data,
            self_instance=self,
            context=_init_context_var.get(),
        )
