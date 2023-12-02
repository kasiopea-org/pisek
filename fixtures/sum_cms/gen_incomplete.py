#!/usr/bin/env python3
# Does not generate any tests for the third subtask.

import sys
import os

test_dir = sys.argv[1]
os.makedirs(test_dir, exist_ok=True)

with open(os.path.join(test_dir, "01_01.in"), "w") as f:
    f.write("1 2")

with open(os.path.join(test_dir, "03_01.in"), "w") as f:
    f.write("-5 2")
