# Písek ⌛

Tool for developing tasks for programming competitions.
Currently used by:
 - [Kasiopea](https://kasiopea.matfyz.cz/)
 - [Czech Informatics Olympiad](https://mo.mff.cuni.cz/p/)

## Install

Pisek requires Python ≥ 3.11. Install with pip:
```bash
pip install git+https://github.com/kasiopea-org/pisek
```

For upgrading add `--upgrade`:
```bash
pip install git+https://github.com/kasiopea-org/pisek --upgrade
```
## Testing tasks

First create `config` file as documented [here](https://github.com/kasiopea-org/pisek/blob/master/example-config).
Here are examples for [Kasiopea mode](https://github.com/kasiopea-org/pisek/blob/master/fixtures/sum_kasiopea/config)
and [CMS mode](https://github.com/kasiopea-org/pisek/blob/master/fixtures/sum_cms/config).

```bash
pisek
```

This command tests this task. It tests all task parts (generator, checker, solutions and judge).

### Task testing overview

What pisek tests (roughly in order):
 - Samples exist and are not empty
 - Generator generates input
    - In Kasiopea mode generator respects seed and is deterministic
 - Checker validates all inputs.
    - Inputs for harder subtasks are harder.
 - Judge works
    - Works on samples
    - Doesn't break on malicious output
 - Solutions run as expected
    - Get expected number of points
    - Succeed/fail on subtasks
 - Data (inputs and outputs) are ok
    - In correct encoding, no unprintable characters and with final newline
    - For Kasiopea mode files are reasonably small

### Testing given programs

For fast testing of a solution `solve_cool.cpp` write:
```bash
pisek test solution solve_cool
```
(Don't write suffix `.cpp`)

For testing on multiple inputs use (only Kasiopea mode) write:
```bash
pisek test solution solve_cool -n 42
```

Similarly generator can be tested using.
```bash
pisek test generator
```

### Useful options

For not stopping on first failure:
```bash
pisek --full
```

Use different time limit (in seconds) for testing solutions:
```bash
pisek --timeout 5
```

For final check. Interprets warnings as failures:
```bash
pisek --strict
```

### Cleaning

Pisek can create a lot of files used for testing. Remove them by running:
```bash
pisek clean
```

### Visualization

For visualizing running time after the solution:
```bash
pisek              # test the task
pisek extract      # extract data
pisek visualize    # visualize
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

       (c)   2019 - 2022 Václav Volhejn <vaclav.volhejn@gmail.com>
       (c)   2019 - 2022 Jiří Beneš <mail@jiribenes.com>
       (c)   2020 - 2022 Michal Töpfer <michal.topfer@gmail.com>
       (c)   2022        Jiri Kalvoda <jirikalvoda@kam.mff.cuni.cz>
       (c)   2023        Daniel Skýpala <skipy@kam.mff.cuni.cz>
