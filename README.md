# Pisek ⌛

Tool for developing tasks for programming competitions.
Currently used by:
 - [Kasiopea](https://kasiopea.matfyz.cz/)
 - [Czech Informatics Olympiad](https://mo.mff.cuni.cz/p/)

And was used by:
 - [CEOI 2024](https://ceoi2024.fi.muni.cz/)

## Install

Pisek requires Python ≥ 3.11. Install with pip:
```bash
pip install pisek
```

For upgrading add `--upgrade`:
```bash
pip install pisek --upgrade
```
## Testing tasks

First create a `config` file as documented [here](https://github.com/kasiopea-org/pisek/blob/master/config-v2-documentation).
You can also reference the examples for
[Kasiopea mode](https://github.com/kasiopea-org/pisek/blob/master/fixtures/sum_kasiopea/config)
and [CMS mode](https://github.com/kasiopea-org/pisek/blob/master/fixtures/sum_cms/config).

```bash
pisek test
```

This command tests the task in the current directory.
It tests all task parts (generator, checker, solutions and judge).

### Task testing overview

What pisek verifies:
 - Samples exist
 - The generator generates inputs
    - Generator is deterministic
    - Generator respects seed on seeded inputs
 - The checker accepts all inputs
 - The judge works
    - It accepts the samples
    - It doesn't crash on malicious output
 - The solutions finish as expected
    - They get the expected number of points
    - They succeed/fail on each subtask as expected
 - Data files (inputs and outputs) are valid
    - They are in the correct encoding
    - They don't contain unprintable characters
    - They have a newline at the end
    - The files are reasonably small
 - The task is complete
    - A CMS judge has no redundant lines in its stdout/stderr
    - If `solution_for_each_subtask=on`, there exists a dedicated solution for each subtask
 

### Testing given programs

For fast testing of only the solution `solve_cool.cpp` use:
```bash
pisek test solution solve_cool
```

Similarly the generator can be tested using:
```bash
pisek test generator
```

### Cleaning

Pisek can create a lot of files used for testing. Remove them by running:
```bash
pisek clean
```

### Visualization

For visualizing the running time for each solution and testcase:
```bash
pisek test --testing-log  # test the task
pisek visualize      # visualize
```

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

```
Copyright (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
Copyright (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
Copyright (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
Copyright (c)   2022        Jiří Kalvoda <jirikalvoda@kam.mff.cuni.cz>
Copyright (c)   2023        Daniel Skýpala <skipy@kam.mff.cuni.cz>
Copyright (c)   2024        Benjamin Swart <benjaminswart@email.cz>
Copyright (c)   2024        Antonín Maloň <git@tonyl.eu>
```
