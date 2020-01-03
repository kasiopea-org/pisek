#!/usr/bin/env python3
t = int(input())
for i in range(t):
    a, b = [int(x) for x in input().split()]
    c = a + b
    if i == 9:
        c += 1
    print(c)
