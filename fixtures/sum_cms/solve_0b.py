#!/usr/bin/env python3
a, b = [int(x) for x in input().split()]

if b % 2 == 0:
    b += 1

print(a + b)
