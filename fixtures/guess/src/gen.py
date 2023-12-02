#!/usr/bin/env python3

import random
import sys
import os

INPUTS = 5

test_dir = sys.argv[1]
os.makedirs(test_dir, exist_ok=True)

random.seed(123)

n = random.sample(range(1, 11), INPUTS)
for i in range(INPUTS):
    test_filename = "{}.in".format(i + 1)
    with open(os.path.join(test_dir, test_filename), "w") as f:
        f.write(str(n[i]) + "\n")
