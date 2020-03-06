import os
import difflib
from typing import Optional, Iterator

from .compile import supported_extensions

DEFAULT_TIMEOUT = 360


def files_are_equal(file_a: str, file_b: str) -> bool:
    """
    Checks if the contents of `file_a` and `file_b` are equal,
    ignoring leading and trailing whitespace.

    If one or both files don't exist, False is returned.
    """

    try:
        with open(file_a, "r") as fa:
            with open(file_b, "r") as fb:
                while True:
                    la = fa.readline()
                    lb = fb.readline()
                    if not la and not lb:
                        # We have reached the end of both files
                        return True
                    # ignore leading/trailing whitespace
                    la = la.strip()
                    lb = lb.strip()
                    if la != lb:
                        return False
    except FileNotFoundError:
        return False


def diff_files(
    file_a: str,
    file_b: str,
    file_a_name: Optional[str] = None,
    file_b_name: Optional[str] = None,
) -> Iterator[str]:
    """
    Produces a human-friendly diff of `file_a` and `file_b`
    as a string iterator.

    Uses `file_a_name` and `file_b_name` for specifying
    a human-friendly name for the files.
    """
    if file_a_name is None:
        file_a_name = file_a
    if file_b_name is None:
        file_b_name = file_b

    try:
        with open(file_a, "r") as fa:
            lines_a = [line.strip() + "\n" for line in fa.readlines()]
    except FileNotFoundError:
        lines_a = [f"({file_a_name} neexistuje)"]

    try:
        with open(file_b, "r") as fb:
            lines_b = [line.strip() + "\n" for line in fb.readlines()]
    except FileNotFoundError:
        lines_b = [f"({file_b_name} neexistuje)"]

    diff = difflib.unified_diff(
        lines_a, lines_b, fromfile=file_a_name, tofile=file_b_name, n=2
    )

    return diff


def resolve_extension(path: str, name: str) -> Optional[str]:
    """
    Given a directory and `name`, finds a file named `name`.[ext],
    where [ext] is a file extension for one of the supported languages.

    If a name with a valid extension is given, it is returned unchanged
    """
    # TODO: warning/error if there are multiple candidates
    extensions = supported_extensions()
    for ext in extensions:
        if os.path.isfile(os.path.join(path, name + ext)):
            return name + ext
        if name.endswith(ext) and os.path.isfile(os.path.join(path, name)):
            # Extension already present
            return name

    return None


def get_data_dir(task_dir: str) -> str:
    return os.path.join(task_dir, "data/")


def get_input_name(seed: int, subtask: int) -> str:
    return f"{seed:x}_{subtask}.in"


def get_output_name(input_file: str, solution_name: str) -> str:
    """
    >>> get_output_name("sample.in", "solve_6b")
    'sample.solve_6b.out'
    """
    return "{}.{}.out".format(
        os.path.splitext(os.path.basename(input_file))[0], solution_name
    )
