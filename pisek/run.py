import subprocess

# TODO: Adapt the code from https://gist.github.com/s3rvac/f97d6cbdfdb15c0a32e7e941f7f4a3fa
#       to limit the memory of the subprocess


def run(executable: str, input_file: str, output_file: str, timeout: int = 100) -> None:
    with open(input_file, "r") as inp:
        with open(output_file, "w") as outp:
            result = subprocess.run(
                executable,
                stdin=inp,
                stdout=outp,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
            result.check_returncode()  # raises an exception if return code != 0
