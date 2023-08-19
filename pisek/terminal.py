from ansi.color import fg, fx
from typing import Callable

from pisek.env import Env

MSG_LEN = 25
def pad(text: str, length: int, pad_char: str = " "):
    return text + (length - len(text))*pad_char

def tab(text: str, tab_str: str="  "):
    return tab_str + text.replace('\n', f"\n{tab_str}")

def plain_variant(f: Callable) -> Callable:
    def g(msg: str, env : Env, *args, **kwargs):
        if env.get_without_log('plain'):
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
