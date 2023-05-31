import os

from pisek.tests.jobs import Job

class TaskJob(Job):
    """Job class that implements useful methods"""
    def _file_exists(self, filename: str):
        self._access_file(filename)
        return os.path.isfile(os.path.join(filename))
    
    def _file_not_empty(self, filename: str):
        self._access_file(filename)
        return os.path.getsize(os.path.join(filename)) > 0

    def _files_equal(self, file_a: str, file_b: str) -> bool:
        """
        Checks if the contents of `file_a` and `file_b` are equal,
        ignoring leading and trailing whitespace.

        If one or both files don't exist, False is returned.
        """
        self._access_file(file_a)
        self._access_file(file_b)
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
