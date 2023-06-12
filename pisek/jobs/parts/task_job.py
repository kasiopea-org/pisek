import os
import shutil
import glob
from typing import List, Tuple, Optional, Any, Callable

from pisek.jobs.cache import CacheResultEnum
import pisek.util as util
from pisek.env import Env
from pisek.task_config import SubtaskConfig
from pisek.jobs.jobs import Job, JobManager
from pisek.jobs.status import StatusJobManager

BUILD_DIR = "build/"

Verdict = CacheResultEnum('ok', 'partial', 'wrong_answer', 'error', 'timeout')
RESULT_MARK = {
    'ok': '·',
    'partial': 'P',
    'error' : '!',
    'timeout': 'T',
    'wrong_answer': 'W'
}

class TaskHelper: 
    def _get_build_dir(self) -> str:
        return BUILD_DIR

    def _resolve_path(self, *path: List[str]):
        return os.path.normpath(os.path.join(self._env.task_dir, *path))

    def _executable(self, name: str) -> str:
        return self._resolve_path(self._get_build_dir(), name)

    def _sample(self, name: str) -> str:
        return self._resolve_path(self._env.config.samples_subdir, name)

    def _data(self, name: str) -> str:
        return self._resolve_path(self._env.config.data_subdir, name)

    def _output(self, input_name: str, solution: str):
        return self._data(util.get_output_name(input_name, solution))


class TaskJobManager(StatusJobManager, TaskHelper):
    """JobManager class that implements useful methods"""
    def _get_samples(self) -> Optional[List[Tuple[str, str]]]:
        """Returns the list [(sample1.in, sample1.out), …]."""
        ins = glob.glob(self._resolve_path("sample*.in"))
        outs = list(map(lambda inp: os.path.splitext(inp)[0] + ".out", ins))
        return [tuple(map(os.path.basename, (ins[i], outs[i]))) for i in range(len(ins))]

    def _all_inputs(self) -> List[str]:
        return list(sorted(set(
            sum([self._subtask_inputs(subtask) for _, subtask in sorted(self._env.config.subtasks.items())], start=[])
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

class TaskJob(Job, TaskHelper):
    """Job class that implements useful methods"""
    @staticmethod
    def _file_access(files: int):
        def dec(f: Callable[...,Any]) -> Callable[...,Any]:
            def g(self, *args, **kwargs):
                for i in range(files):
                    self._access_file(args[i])
                return f(self, *args, **kwargs)
            return g
        return dec

    @_file_access(1)
    def _open_file(self, filename: str, mode='r', **kwargs):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        return open(filename, mode, **kwargs)

    @_file_access(1)
    def _file_exists(self, filename: str):
        return os.path.isfile(os.path.join(filename))

    @_file_access(1)
    def _file_not_empty(self, filename: str):
        return os.path.getsize(os.path.join(filename)) > 0
    
    @_file_access(2)
    def _copy_file(self, filename: str, dst: str):
        return shutil.copy(filename, dst)

    @_file_access(2)
    def _files_equal(self, file_a: str, file_b: str) -> bool:
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
