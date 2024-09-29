# Batch judge

Batch judge gets contestant output, input and correct output.
It should say whether the contestant output is correct.

There are various types of judges you can use:
- `tokens` - fast, versatile file equality checker
- `diff` - file equality checker based on command line tool (don't use, has quadratic time complexity)
- `judge` - custom judge

If there is only single correct output (minimum of an array), `tokens` is strongly recommended.
Otherwise, when there are multiple correct outputs (shortest path in a graph), writing custom judge is necessary. Set `out_check` in config accordingly.

## Tokens judge

Fast and versatile equality checker. Ignores whitespace, but not newlines.

You can customize tokens judge with `tokens_ignore_newlines` or `tokens_ignore_case`.
For comparing floats, set `tokens_float_rel_error` and `tokens_float_abs_error`.
Details can be found in [config-documentation](/config-v3-documentation).

## Diff judge

Equality judge based on diff tool. Runs `diff -Bbq` under the hood.
Ignores whitespace and empty lines.

**Use is strongly discouraged because of quadratic complexity of `diff`.**

## Custom judge

If there can be multiple correct solutions, it is necessary to write custom judge.
Set `out_judge` to source code path of your judge, `judge_type` to *ehm* judge type (see below).
And `judge_needs_in`, `judge_needs_out` to `0`/`1` depending whether judge needs input and correct output.

When writing custom judge, you can chose from multiple judge types: 
1. [cms-batch judge](#cms-batch-judge)
2. [opendata-v1](#opendata-v1-judge)

### Cms-batch judge

CMS batch judge format as described in [CMS documentation](https://cms.readthedocs.io/en/v1.4/Task%20types.html?highlight=Manager#checker).

It is run as following (having given filenames as arguments):
```
./judge [input] [correct output] [contestant output]
```

The judge should print a relative number of points (float between 0.0 and 1.0) to it's stdout to single-line.
To it's stderr it should write single-line message to the contestant.
**Unlike in CMS documentation the files should be single-line only.** There will be warning otherwise.

### Opendata-v1 judge

Opendata-v1 judge is run in this way:
```
./judge [subtask] [seed] < contestant-output
```
Where `subtask` is the input's subtask and `seed` it's generating seed.
(The arguments are equivalent to `opendata-v1` generator this input has been generated with.)
If the input was not generated with seed, `seed` can be anything.

If `judge_needs_in` is set, judge will get input filename in `TEST_INPUT`
environment variable. Similarly, if `judge_needs_out` is set, correct output
filename will be in `TEST_OUTPUT` environment variable.

If the output is correct, the judge should exit with returncode 0.
Otherwise, the judge should exit returncode 1.

