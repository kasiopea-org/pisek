def diff(path_a, path_b):
    with open(path_a, "r") as fa:
        with open(path_b, "r") as fb:
            while True:
                la = fa.readline()
                lb = fb.readline()
                if not la and not lb:
                    # We have reached the end of both files
                    return True
                la = la.strip()
                lb = lb.strip()
                if la != lb:
                    return False
