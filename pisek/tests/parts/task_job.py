import os
import glob
from typing import List, Tuple

from pisek.env import Env
from pisek.task_config import SubtaskConfig
from pisek.tests.jobs import Job, JobManager

class TaskJobManager(JobManager):
    """JobManager class that implements useful methods"""
    def _resolve_path(self, *path):
        return os.path.normpath(os.path.join(self._env.task_dir, *path))

    def _get_samples(self) -> List[Tuple[str, str]]:
        """Returns the list [(sample1.in, sample1.out), …]."""
        ins = glob.glob(self._resolve_path("sample*.in"))
        outs = []
        for inp in ins:
            out = os.path.splitext(inp)[0] + ".out"
            if not os.path.isfile(out):
                self.fail(f"No matching output {out} for input {inp}.")
            outs.append(out)
        return [tuple(map(os.path.basename, (ins[i], outs[i]))) for i in range(len(ins))]
    
    def _all_inputs(self) -> List[str]:
        return list(sorted(set(
            sum([self._subtask_inputs(subtask, self._env) for subtask in self._env.config.subtasks], start=[])
        )))

    def _subtask_inputs(self, subtask: SubtaskConfig) -> List[str]:
        data_dir = self._env.config.get_data_dir()
        # XXX: As we iterate through all inputs we don't want to log this.
        globs = subtask.get_without_log('in_globs')

        input_filenames: List[str] = []
        for g in globs:
            input_filenames += [
                os.path.basename(f) for f in glob.glob(os.path.join(data_dir, g))
            ]
        input_filenames.sort()

        return input_filenames

class TaskJob(Job):
    """Job class that implements useful methods"""
    def _open_file(self, filename: str, mode='r', **kwargs):
        self._access_file(filename)
        return open(filename, mode, **kwargs)

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
    
    def _resolve_path(self, *path: List[str]):
        return os.path.normpath(os.path.join(self._env.task_dir, *path))

    def _sample(self, name: str) -> str:
        return self._resolve_path(self._env.config.samples_subdir, name)

    def _data(self, name: str) -> str:
        return self._resolve_path(self._env.config.data_subdir, name)
