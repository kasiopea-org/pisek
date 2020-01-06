#!/usr/bin/env python3
# For testing that a Python generator works as well

import random
import sys

diff = int(sys.argv[1]) - 1
seed = int(sys.argv[2], 16)
random.seed(seed)

MAX_ABS = [int(1e9), int(1e18)][diff]

T = 10
print(T)

for ti in range(T):
    a = random.randint(-MAX_ABS, MAX_ABS)
    b = random.randint(-MAX_ABS, MAX_ABS)
    print(a, b)
