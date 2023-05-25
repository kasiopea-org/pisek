# pisek  - Nástroj na přípravu úloh do programátorských soutěží, primárně pro soutěž Kasiopea.
#
# Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
# Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
# Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
# Copyright (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from ..task_config import TaskConfig
from .kasiopea_test_suite import kasiopea_test_suite
from .cms_test_suite import cms_test_suite


def get_test_suite(dir, **kwargs):
    config = TaskConfig(dir)

    suites_dict = {
        "kasiopea": kasiopea_test_suite,
        "cms": cms_test_suite,
    }

    try:
        suite = suites_dict[config.contest_type](dir, **kwargs)
    except KeyError:
        raise KeyError(
            f"Neznámý typ soutěže '{config.contest_type}'. "
            f"Znám typy {list(suites_dict)}",
        )

    return suite
