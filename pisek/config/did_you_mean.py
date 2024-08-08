from abc import ABC, abstractmethod
import editdistance
from importlib.resources import files
import re
from typing import Callable, Optional


CONFIG_DESCRIPTION = str(files("pisek").joinpath("config/config-description"))

sections = []
keys = []

def regex_cmp(regex: str, name: str) -> int:
    if re.match(regex, name):
        return 0
    else:
        return 10


class ApplicabilityCondition(ABC):
    @abstractmethod
    def check(self, config: "ConfigHeirarchy") -> Optional[str]:
        pass

class HasKeyValue(ApplicabilityCondition):
    def __init__(self, section: str, key: str, value: str) -> None:
        self.section = section
        self.key = key
        self.value = value
        super().__init__()
    
    def check(self, config: "ConfigHeirarchy") -> Optional[str]:
        current_value = config.get(self.section, self.key)
        if current_value == self.value:
            return None
        return f"[{self.section}] {self.key}={current_value}"

class ConfigDescriptionKey:
    def __init__(self, section: str, key: str) -> None:
        self.section = section
        self.key = key
        self.section_similarity: Optional[Callable[[str, str], int]] = None
        self.key_similarity: Optional[Callable[[str, str], int]] = None
        self.applicability_conditions: list[ApplicabilityCondition] = []

    def score(self, section: str, key: str) -> int:
        score = 0
        if self.key_similarity is None:
            score += editdistance.distance(self.key, key)
        else:
            score += self.key_similarity(self.key, key)

        if self.section_similarity is None:
            score += 5 * editdistance.distance(self.section, section)
        else:
            score += self.section_similarity(self.section, section)

        return score

    def applicable(self, config: "ConfigHierarchy") -> Optional[str]:
        for cond in self.applicability_conditions:
            if not cond(config):
                return 

class ConfigKeysHelper:
    def __init__(self) -> None:
        self.sections: list[str] = []
        self.keys: list[ConfigDescriptionKey] = []
        with open(CONFIG_DESCRIPTION) as f:
            last_key: Optional[ConfigDescriptionKey] = None
            section_name: str = ""
            section_similarity = None
            for line in f:
                line = line.strip()

                if len(line) == 0:
                    pass

                elif line.startswith("#!"):
                    [fun, *args] = line.removeprefix("#!").split()
                    if fun == "regex":
                        if last_key is None:
                            section_similarity = regex_cmp
                        else:                    
                            last_key.key_similarity = regex_cmp
                    elif fun == "if":
                        if len(args) != 1 or args[0].count("=") != 1:
                            raise ValueError(f"invalid config-description function if arguments: '{' '.join(args)}'")
                        key, value = args[0].split("=")
                        last_key.applicability_conditions.append(HasKeyValue(section_name, key, value))
                    else:
                        raise ValueError(f"invalid config-description function: '{fun}'")

                elif line.count("=") == 1 and line[-1] == "=":
                    last_key = ConfigDescriptionKey(section_name, line.removesuffix("="))
                    self.keys.append(last_key)
                    last_key.section_similarity = section_similarity

                elif line[0] == "[" and line[-1] == "]":
                    last_key = None
                    section_similarity = None
                    section_name = line.removeprefix("[").removesuffix("]")
                    self.sections.append(section_name)

                else:
                    raise ValueError(f"invalid config-description line: '{line}'")

