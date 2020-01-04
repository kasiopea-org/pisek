import subprocess


def run(executable: str, input_file: str, output_file: str, timeout: int = 100) -> bool:
    # TODO: Adapt the code from https://gist.github.com/s3rvac/f97d6cbdfdb15c0a32e7e941f7f4a3fa
    #       to limit the memory of the subprocess
    with open(input_file, "r") as inp:
        with open(output_file, "w") as outp:
            result = subprocess.run(
                executable,
                stdin=inp,
                stdout=outp,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )

            return result.returncode == 0


def run_direct(executable: str):
    """ like run(), but with no redirections or timeout """
    result = subprocess.run(executable, stderr=subprocess.PIPE)

    return result.returncode == 0
