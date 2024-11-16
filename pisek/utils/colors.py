from colorama import Fore


class __ColorSettings:
    """Singleton object to store current color settings."""

    def __init__(self) -> None:
        self.colors_on = True

    def set_state(self, colors_on: bool) -> None:
        """Sets whether colors should be displayed."""
        self.colors_on = colors_on

    def colored(self, msg: str, color: str) -> str:
        """Recolors all white text to given color."""
        if not self.colors_on:
            return msg

        col = getattr(Fore, color.upper())
        msg = msg.replace(f"{Fore.RESET}", f"{Fore.RESET}{col}")
        return f"{col}{msg}{Fore.RESET}"


ColorSettings = __ColorSettings()
