import termcolor
from typing import Any, Optional

from pisek.env import Env
from pisek.jobs.cache import CacheResultEnum
from pisek.jobs.jobs import State, Job, JobManager
from pisek.jobs.status import tab
from pisek.jobs.parts.task_job import TaskJob, TaskJobManager
from pisek.jobs.parts.program import RunResult, RunResultKind, ProgramJob, Compile


CheckerResult = CacheResultEnum('ok', 'failed')
class CheckerManager(TaskJobManager):
    def __init__(self):
        self.skipped_checker = ""
        super().__init__("Checker Manager")

    def _get_jobs(self) -> list[Job]:
        if self._env.config.checker is None:
            if self._env.strict:
                return self.fail("No checker specified in config.")
            self.skipped_checker = termcolor.colored(
                "Warning: No checker specified in config.\n"
                "It is recommended to set `checker` is section [tests]",
            color="yellow")
        if self._env.no_checker:
            self.skipped_checker = termcolor.colored("Skipping checking", color="yellow")

        if self.skipped_checker != "":
            return []

        checker = self._resolve_path(self._env.config.checker)

        jobs = [compile := Compile(checker, self._env.fork())]
        
        self.loose_subtasks = []
        for sub_num, sub, new_env in self._env.iterate("config.subtasks", self._env):
            for inp in self._subtask_inputs(sub):
                jobs.append(check := CheckerJob(checker, inp, sub_num, RunResultKind.OK, new_env.fork()))
                check.add_prerequisite(compile)

        for sub_num, sub, new_env in self._env.iterate("config.subtasks", self._env):
            if sub.predecessors:
                self.loose_subtasks.append(LooseCheckJobGroup(sub_num))
                for pred in sub.predecessors:
                    self.loose_subtasks[-1].jobs[pred] = []
                    for inp in self._subtask_new_inputs(sub):
                        jobs.append(check := CheckerJob(checker, inp, pred, None, new_env.fork()))
                        self.loose_subtasks[-1].jobs[pred].append(check)
                        check.add_prerequisite(compile)

        return jobs
    
    def _evaluate(self) -> Any:
        if len(self.jobs) == 0:
            return

        for loose_subtask in self.loose_subtasks:
            err = loose_subtask.failed(self._env.config.fail_mode)
            if err is not None:
                return self.fail(err)

    def _get_status(self) -> str:
        if self.skipped_checker:
            if self.state == State.succeeded:
                return self.skipped_checker
            else:
                return ""
        else:
            return super()._get_status()

class LooseCheckJobGroup:
    def __init__(self, num: int):
        self.num = num
        self.jobs = {}

    def failed(self, fail_mode: str) -> Optional[str]:
        for pred in self.jobs:
            results = list(map(lambda x: x.result.kind, self.jobs[pred]))
            if fail_mode == "all" and RunResultKind.OK in results:
                job = self._index_job(pred, results, RunResultKind.OK)
                return (
                    f"Checker is not strict enough:\n"
                    f"All inputs of subtask {self.num} should have not passed on predecessor subtask {pred}\n"
                    f"but on input {job.input_name} did not."
                )
            if fail_mode == "any" and RunResultKind.RUNTIME_ERROR not in results:
                return (
                    f"Checker is not strict enough:\n"
                    f"An input of subtask {self.num} should have not passed on predecessor subtask {pred}\n"
                    f"but all have passed."
                )
            if RunResultKind.TIMEOUT in results:
                job = self._index_job(pred, results, RunResultKind.TIMEOUT)
                return (
                    f"Checker timeouted on input {job.input_name}, subtask {self.num}."
                )

    def _index_job(self, pred: int, results: list[RunResultKind], result: RunResultKind) -> Job:
        return self.jobs[pred][results.index(result)]


class CheckerJob(ProgramJob):
    def __init__(self, checker: str, input_name: str, subtask: int, expected: Optional[RunResultKind], env: Env):
        self.subtask = subtask
        super().__init__(
            name=f"Check {input_name} on subtask {subtask}",
            program=checker,
            env=env
        )
        self.input_name = input_name
        self.input_file = self._data(input_name)
        self.expected = expected

    def _check(self) -> RunResult:
        return self._run_program(
            [str(self.subtask)],
            stdin=self.input_file
        )

    def _run(self) -> None:
        result = self._check()
        if result is None:
            return
        if self.expected == RunResultKind.OK != result.kind:
            return self._program_fail(
                f"Checker failed on {self.input_name} (subtask {self.subtask}) but should have succeeded.", result
            )
        elif self.expected == RunResultKind.RUNTIME_ERROR != result.kind:
            return self._program_fail(
                f"Checker succeeded on {self.input_name} (subtask {self.subtask}) but should have failed.", result
            )
        return result
