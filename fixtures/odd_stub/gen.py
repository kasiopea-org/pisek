#!/usr/bin/env python3

from random import Random
import os
import sys

random = Random(275)
directory = sys.argv[1]

for i in range(10):
    nums = set()

    n = random.randint(300000, 400000)
    for _ in range(n):
        nums.add(random.randint(1, 1_000_000))

    nums = list(nums)
    random.shuffle(nums)

    filename = f"{i:02}.in"

    with open(os.path.join(directory, filename), "w") as f:
        for num in nums:
            f.write(f"{num}\n")
