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
import sys

from ansi.color import fg, fx
from typing import Callable

from pisek.env import Env

MSG_LEN = 25


def eprint(msg, *args, **kwargs):
    print(msg, *args, file=sys.stderr, **kwargs)


def pad(text: str, length: int, pad_char: str = " "):
    return text + (length - len(text)) * pad_char


def tab(text: str, tab_str: str = "  "):
    return tab_str + text.replace("\n", f"\n{tab_str}")


def plain_variant(f: Callable) -> Callable:
    def g(msg: str, env: Env, *args, **kwargs):
        if env.plain:
            return msg
        else:
            return f(msg, *args, **kwargs)

    return g


@plain_variant
def colored(msg: str, color: str) -> str:
    # Recolors all white text to given color
    col = getattr(fg, color)
    msg = msg.replace(f"{fx.reset}", f"{fx.reset}{col}")
    return f"{col}{msg}{fx.reset}"
