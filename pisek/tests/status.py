import os
from termcolor import colored

from pisek.tests.jobs import JobManager

MSG_LEN = 20
BAR_LEN = 40

def pad(text: str, lenght: int, pad_char : str = " "):
    return text + (lenght - len(text))*pad_char

class StatusJobManager(JobManager):
    def _bar(self, msg: str, part: int, full: int) -> str:
        bar_color = "green" if part == full else "cyan"
        filled = BAR_LEN * part // full
        return f"{pad(msg, MSG_LEN)}{colored(filled*'━', color=bar_color)}{colored((BAR_LEN-filled)*'━', color='grey')}  ({part}/{full})"

    def _job_bar(self, msg: str) -> str:
        return self._bar(msg, self._finished_jobs(), len(self.jobs))
    
    def _get_status(self) -> str:
        return self._job_bar(self.name)
