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
