# Communication judge

Communication judge gets input and means of communication with contestant's solution.
It should report whether contestant solution is correct.

There is currently only one communication `judge_type` supported:

## Cms-communication judge
*See [CMS documentation](https://cms.readthedocs.io/en/v1.4/Task%20types.html?highlight=Manager#communication) for more, however only one user process is supported.*

The solution and the judge run simultaneously. They communicate via FIFO (named pipes).

The judge is run:
```
./judge [FIFO from solution] [FIFO to solution] < input
```
FIFO's point to solution's stdout and stdin respectively.

The judge should print a relative number of points (float between 0.0 and 1.0) to it's stdout to single-line.
To it's stderr it should write single-line message to the contestant.
**Unlike in CMS documentation the files should be single-line only.** There will be warning otherwise.
