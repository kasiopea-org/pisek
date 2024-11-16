# pisek cms - Tool for importing tasks from Pisek into CMS.
#
# Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from cms.db.task import Dataset, Testcase
from cms.db.filecacher import FileCacher
from sqlalchemy.orm import Session
from glob import glob
from itertools import chain

from pisek.env.env import Env
from pisek.config.config_types import TaskType
from pisek.utils.paths import TaskPath


def create_testcase(
    session: Session,
    files: FileCacher,
    dataset: Dataset,
    codename: str,
    input_file: TaskPath,
    output_file: TaskPath | None,
) -> Testcase:
    input = files.put_file_from_path(input_file.path, f"Input for testcase {codename}")

    if output_file is not None:
        output = files.put_file_from_path(
            output_file.path, f"Output for testcase {codename}"
        )
    else:
        output = files.put_file_content(
            "No output".encode(), "Almost empty output file"
        )

    testcase = Testcase(
        dataset=dataset, codename=codename, input=input, output=output, public=True
    )

    session.add(testcase)
    return testcase
