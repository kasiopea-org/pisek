# Communication judge

The communication judge gets the input and means of communication with contestant's solution.
It should report whether the contestant solution is correct.

There is currently only one communication `judge_type` supported:

## CMS-communication judge
*See [CMS documentation](https://cms.readthedocs.io/en/v1.4/Task%20types.html?highlight=Manager#communication) for more, however only one user process is supported.*

The solution and the judge run simultaneously. They communicate via FIFO (named pipes).

The judge is run:
```
./judge [FIFO from solution] [FIFO to solution] < input
```
FIFOs point to the solutions stdout and stdin respectively.

The judge should print a relative number of points (a float between 0.0 and 1.0) to it's stdout as a single line.
To its stderr it should write a single-line message to the contestant.
**Unlike the CMS documentation specifies, the files should be single-line only.**
There will be a warning otherwise.
