#!/usr/bin/env python3

from random import Random
import os
import sys

if len(sys.argv) == 1:
    print("random-uniform repeat=10")
    exit()

assert sys.argv[1] == "random-uniform"
random = Random(int(sys.argv[2], base=16))

nums = set()

n = random.randint(300000, 400000)
for _ in range(n):
    nums.add(random.randint(1, 1_000_000))

nums = list(nums)
random.shuffle(nums)

for num in nums:
    print(num)
