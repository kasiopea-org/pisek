from math import inf
import os
from termcolor import colored

from pisek.jobs.jobs import State, PipelineItem, JobManager

try:
    terminal_width, terminal_height = os.get_terminal_size()
except OSError:
    terminal_width, terminal_height = 100, inf

MSG_LEN = 25
MAX_BAR_LEN = 60
line_sepatator = '⎯'*terminal_width + '\n'

def pad(text: str, lenght: int, pad_char: str = " "):
    return text + (lenght - len(text))*pad_char

def tab(text: str, tab_str: str="  "):
    return tab_str + text.replace('\n', f"\n{tab_str}")


class StatusJobManager(JobManager):
    """JobManager that implements useful methods for terminal interaction."""
    @staticmethod
    def _bar(msg: str, part: int, full: int, color : str = "cyan") -> str:
        """Return progress bar with given parameters."""
        msg = pad(msg, MSG_LEN)
        progress_msg = f"  ({part}/{full})"

        bar_len = min(terminal_width - len(msg) - len(progress_msg), MAX_BAR_LEN)
        filled = bar_len * part // full

        return f"{msg}{colored(filled*'━', color=color)}{colored((bar_len-filled)*'━', color='grey')}{progress_msg}"

    def _job_bar(self, msg: str) -> str:
        """Returns progress bar according to status of this manager's jobs."""
        color = "cyan"
        if self.state == State.canceled:
            return f"{pad(msg, MSG_LEN)}{colored('canceled', color='yellow')}"
        elif self.state == State.succeeded:
            color = "green"
        elif self.state == State.failed or State.failed in self._job_states():
            color = "red"

        return self._bar(msg, len(self._jobs_with_state(State.succeeded)), max(1, len(self.jobs)), color=color)
    
    def _get_status(self) -> str:
        return self._job_bar(self.name)

    @staticmethod
    def _fail_message(pitem: PipelineItem) -> str:
        """Get fail message of given job."""
        return f'"{pitem.name}" failed:\n{tab(pitem.fail_msg)}\n'

    def failures(self) -> str:
        """Returns failures of failed jobs."""
        fails = []
        for job in self._jobs_with_state(State.failed):
            fails.append(self._fail_message(job))

        if self.fail_msg != "":
            fails.append(self._fail_message(self))

        msg = line_sepatator + line_sepatator.join(fails) + line_sepatator
        return colored(msg, color="red")
