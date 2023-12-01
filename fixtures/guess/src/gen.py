#!/usr/bin/env python3

import random
import sys
import os

test_dir = sys.argv[1]
os.makedirs(test_dir, exist_ok=True)

random.seed(123)

for i in range(3):
    a = random.randint(1, 10)

    test_filename = "{}.in".format(i + 1)
    with open(os.path.join(test_dir, test_filename), "w") as f:
        f.write(str(a) + "\n")
