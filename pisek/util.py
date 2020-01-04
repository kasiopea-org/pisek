import os


def files_are_equal(file_a: str, file_b: str) -> bool:
    """
    Checks if the contents of `file_a` and `file_b` are equal,
    ignoring leading and trailing whitespace
    """
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


def resolve_extension(path, name):
    """
    Given a directory and `name`, finds a file named `name`.[ext],
    where [ext] is a file extension for one of the supported languages.

    If a name with a valid extension is given, it is returned unchanged
    """
    # TODO: warning/error if there are multiple candidates
    extensions = [".cpp", ".py"]
    for ext in extensions:
        if os.path.isfile(os.path.join(path, name + ext)):
            return name + ext
        if name.endswith(ext) and os.path.isfile(os.path.join(path, name)):
            # Extension already present
            return name

    return None
