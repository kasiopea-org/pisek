#!/usr/bin/env python3

import random
import sys
import os

test_dir = sys.argv[1]
os.makedirs(test_dir, exist_ok=True)

POSITIVE_ONLY = [True, False, False]
MAX_ABS = [int(1e9), int(1e9), int(1e18)]

random.seed(123)

print("Generating...", file=sys.stderr)
for subtask_i, (positive_only, max_abs) in enumerate(zip(POSITIVE_ONLY, MAX_ABS)):
    for ti in range(5):
        a = random.randint(-max_abs, max_abs)
        b = random.randint(-max_abs, max_abs)
        if positive_only:
            a = abs(a)
            b = abs(b)

        test_filename = "{:0>2}_{:0>2}.in".format(subtask_i + 1, ti + 1)

        with open(os.path.join(test_dir, test_filename), "w") as f:
            f.write("{} {}\n".format(a, b))
