import os
from termcolor import colored

from pisek.jobs.jobs import State, PipelineItem, JobManager

MSG_LEN = 20
BAR_LEN = 40
TOTAL_LEN = 80

LINE_SEPARATOR = '⎯'*TOTAL_LEN + '\n'

def pad(text: str, lenght: int, pad_char: str = " "):
    return text + (lenght - len(text))*pad_char

def tab(text: str, tab_str: str="  "):
    return tab_str + text.replace('\n', f"\n{tab_str}")


class StatusJobManager(JobManager):
    @staticmethod
    def _bar(msg: str, part: int, full: int, color : str = "cyan") -> str:
        filled = BAR_LEN * part // full
        return f"{pad(msg, MSG_LEN)}{colored(filled*'━', color=color)}{colored((BAR_LEN-filled)*'━', color='grey')}  ({part}/{full})"

    def _job_bar(self, msg: str) -> str:
        color = "cyan"
        if self.state == State.canceled:
            return f"{pad(msg, MSG_LEN)}{colored('canceled', color='yellow')}"
        elif self.state == State.succeeded:
            color = "green"
        elif State.failed in self._job_states():
            color = "red"
        
        return self._bar(msg, self._finished_jobs(), len(self.jobs), color=color)
    
    def _get_status(self) -> str:
        return self._job_bar(self.name)

    @staticmethod
    def _fail_message(pitem: PipelineItem) -> str:
        return f'"{pitem.name}" failed:\n{tab(pitem.fail_msg)}\n'

    def failures(self) -> str:
        fails = []
        for job in self._failed_jobs():
            fails.append(self._fail_message(job))

        if self.fail_msg != "":
            fails.append(self._fail_message(self))

        msg = LINE_SEPARATOR + LINE_SEPARATOR.join(fails) + LINE_SEPARATOR
        return colored(msg, color="red")
