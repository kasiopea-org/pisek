# pisek  - Tool for developing tasks for programming competitions.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
# Copyright (c)   2023        Daniel Skýpala <daniel@honza.info>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from pisek.utils.text import tab, pad
from pisek.utils.terminal import MSG_LEN, TARGET_LINE_WIDTH, terminal_width
from pisek.jobs.jobs import State, PipelineItem, JobManager

TARGET_BAR_WIDTH = TARGET_LINE_WIDTH - MSG_LEN - 11
line_sepatator = "⎯" * terminal_width + "\n"


class StatusJobManager(JobManager):
    """JobManager that implements useful methods for terminal interaction."""

    def _bar(self, msg: str, part: int, full: int, color: str = "cyan") -> str:
        """Return progress bar with given parameters."""
        msg = pad(msg, MSG_LEN - 1)
        progress_msg = f"  ({part}/{full})"

        bar_len = min(TARGET_BAR_WIDTH, TARGET_LINE_WIDTH - MSG_LEN - len(progress_msg))
        filled = bar_len * part // full

        return f"{msg} {self._colored(filled*'━', color)}{self._colored((bar_len-filled)*'━', 'white')}{progress_msg}"

    def _job_bar(self, msg: str) -> str:
        """Returns progress bar according to status of this manager's jobs."""
        color = "cyan"
        if self.state == State.cancelled:
            return f"{pad(msg, MSG_LEN-1)} {self._colored('cancelled', 'yellow')}"
        elif self.state == State.succeeded:
            color = "green"
        elif self.state == State.failed or State.failed in self._job_states():
            color = "red"

        return self._bar(
            msg,
            len(self._jobs_with_state(State.succeeded))
            + (self.state == State.succeeded),
            len(self.jobs) + 1,
            color=color,
        )

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
        return self._colored(msg, "red")
