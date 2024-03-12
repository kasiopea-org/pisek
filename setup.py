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

import setuptools

setuptools.setup(
    name="pisek",
    version="1.0",
    description="Tool for developing tasks for programming competitions",
    packages=setuptools.find_packages(),
    install_requires=["PyYAML", "colorama", "pydantic"],
    extras_require={"dev": ["black", "mypy"]},
    entry_points={"console_scripts": ["pisek=pisek.__main__:main_wrapped"]},
    include_package_data=True,
    package_data={"pisek": ["env/global-defaults", "tools/*"]},
)
