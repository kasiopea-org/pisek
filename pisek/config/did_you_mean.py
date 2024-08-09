from abc import ABC, abstractmethod
import editdistance
from importlib.resources import files
import re
from typing import TYPE_CHECKING, Callable, Optional

from pisek.utils.text import tab

from .config_errors import TaskConfigError

if TYPE_CHECKING:
    from .config_hierarchy import ConfigHierarchy

CONFIG_DESCRIPTION = str(files("pisek").joinpath("config/config-description"))


def regex_score(regex: str, name: str) -> int:
    if re.match(regex, name):
        return 0
    else:
        return 5


class ApplicabilityCondition(ABC):
    @abstractmethod
    def check(self, section: str, config: "ConfigHierarchy") -> str:
        pass


class HasKeyValue(ApplicabilityCondition):
    def __init__(
        self,
        section: "ConfigSectionDescription",
        key: "ConfigKeyDescription",
        value: str,
    ) -> None:
        self.section = section
        self.key = key
        self.value = value
        super().__init__()

    def check(self, section: str, config: "ConfigHierarchy") -> str:
        section = self.section.transform_name(section)
        current_value = self.key.get(config, section=section)
        if current_value == self.value:
            return ""
        return f"[{section}] {self.key.key}={current_value}\n"


class ConfigSectionDescription:
    def __init__(self, section: str) -> None:
        self.section = section
        self.defaults_to: list[str] = []
        self.similarity_function: Optional[Callable[[str, str], int]] = None

    def similarity(self, section: str) -> int:
        if self.similarity_function is None:
            return 5
        else:
            return self.similarity_function(self.section, section)

    def transform_name(self, name: str) -> str:
        return name if self.similarity(name) == 0 else self.section


class ConfigKeyDescription:
    def __init__(self, section: ConfigSectionDescription, key: str) -> None:
        self.section = section
        self.key = key
        self.defaults_to: list[tuple[str, str]] = []
        self.applicability_conditions: list[ApplicabilityCondition] = []

    def get(self, config: "ConfigHierarchy", section: str) -> str:
        return config.get_from_candidates(
            [(self.section.transform_name(section), self.key)] + self.defaults()
        ).value

    def defaults(self) -> list[tuple[str, str]]:
        return self.defaults_to + [(d, self.key) for d in self.section.defaults_to]

    def similarity(self, key: str) -> int:
        return editdistance.distance(self.key, key)

    def score(self, section: str, key: str) -> int:
        return self.section.similarity(section) + self.similarity(key)

    def applicable(self, section: str, config: "ConfigHierarchy") -> str:
        text = ""
        for cond in self.applicability_conditions:
            text += cond.check(section, config)
        return text


class ConfigKeysHelper:
    def __init__(self) -> None:
        self.sections: dict[str, ConfigSectionDescription] = {}
        self.keys: dict[tuple[str, str], ConfigKeyDescription] = {}
        add_applicability_conditions: list[
            tuple[ConfigKeyDescription, Callable[[], ApplicabilityCondition]]
        ] = []
        with open(CONFIG_DESCRIPTION) as f:
            section: Optional[ConfigSectionDescription] = None
            last_key: Optional[ConfigKeyDescription] = None
            for line in f:
                line = line.strip()

                if len(line) == 0:
                    pass

                elif line.startswith("#!"):
                    assert section is not None
                    [fun, *args] = line.removeprefix("#!").split()
                    if fun == "regex":
                        assert last_key is None
                        section.similarity_function = regex_score
                    elif fun == "if":
                        assert section is not None
                        assert last_key is not None
                        if len(args) != 2 or args[1].count("=") != 1:
                            self._invalid_function_args(fun, args)
                        key_name, value = args[1].split("=")
                        # Key with key_name might not exist yet
                        add_applicability_conditions.append(
                            (last_key, self._gen_has_keyvalue(args[0], key_name, value))
                        )
                    elif fun == "default":
                        if last_key is None:
                            if len(args) != 1:
                                self._invalid_function_args(fun, args)
                            section.defaults_to.append(args[0])
                        else:
                            if len(args) != 2:
                                self._invalid_function_args(fun, args)
                            last_key.defaults_to.append((args[0], args[1]))
                    else:
                        raise ValueError(
                            f"invalid config-description function: '{fun}'"
                        )

                elif line.count("=") == 1 and line[-1] == "=":
                    assert section is not None
                    last_key = ConfigKeyDescription(section, line.removesuffix("="))
                    self.keys[(section.section, last_key.key)] = last_key

                elif line[0] == "[" and line[-1] == "]":
                    last_key = None
                    section = ConfigSectionDescription(
                        line.removeprefix("[").removesuffix("]")
                    )
                    self.sections[section.section] = section

                else:
                    raise ValueError(f"invalid config-description line: '{line}'")

        for key, lambda_cond in add_applicability_conditions:
            key.applicability_conditions.append(lambda_cond())

    def _gen_has_keyvalue(
        self, section: str, key: str, value: str
    ) -> Callable[[], HasKeyValue]:
        def f():
            return HasKeyValue(self.sections[section], self.keys[(section, key)], value)

        return f

    def _invalid_function_args(self, fun_name: str, args: list[str]) -> None:
        raise ValueError(
            f"invalid config-description function {fun_name} arguments: '{' '.join(args)}'"
        )

    def find_section(self, section: str) -> str:
        return min(
            self.sections.values(),
            key=lambda s: editdistance.distance(section, s.section),
        ).section

    def find_key(
        self, section: str, key: str, config: "ConfigHierarchy"
    ) -> Optional[tuple[str, str]]:
        best_key = min(self.keys.values(), key=lambda k: k.score(section, key))
        if not (text := best_key.applicable(section, config)):
            return (best_key.section.transform_name(section), best_key.key)
        elif best_key.score(section, key) == 0:
            raise TaskConfigError(
                f"Key '{key}' not applicable in this context:\n{tab(text).rstrip()}"
            )
        else:
            return None
