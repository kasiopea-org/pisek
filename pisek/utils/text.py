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

from colorama import Fore
import sys


def tab(text: str, tab_str: str = "  "):
    return tab_str + text.replace("\n", f"\n{tab_str}")


def pad(text: str, length: int, pad_char: str = " "):
    return text + (length - len(text)) * pad_char


def pad_left(text: str, length: int, pad_char: str = " "):
    return pad(text[::-1], length, pad_char)[::-1]


def colored(msg: str, color: str, no_colors: bool = False) -> str:
    """Recolors all white text to given color."""
    if no_colors:
        return msg

    col = getattr(Fore, color.upper())
    msg = msg.replace(f"{Fore.RESET}", f"{Fore.RESET}{col}")
    return f"{col}{msg}{Fore.RESET}"


def eprint(msg, *args, **kwargs):
    """Prints to sys.stderr."""
    print(msg, *args, file=sys.stderr, **kwargs)


def warn(msg: str, err: type, strict: bool = False, no_colors: bool = False) -> None:
    """Warn if strict is False, otherwise raise error."""
    if strict:
        raise err(msg)
    eprint(colored(f"Warning: {msg}", "yellow", no_colors))
