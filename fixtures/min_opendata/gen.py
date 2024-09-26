#!/usr/bin/env python3
from random import randint, seed
import sys

def fail(msg):
    print(msg, file=sys.stderr)
    quit(42)

def gen(max_n):
    n = randint(2, max_n)
    arr = [randint(0, 10**9) for i in range(n)]

    print(n)
    print(" ".join(map(str, arr)))


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("01\n02")
    elif len(sys.argv) == 3:
        _, name, hex_seed = sys.argv
        seed(hex_seed)
        gen([None, 1000, 10**6][int(name)])
    else:
        fail(f"Invalid number of arguments: {len(sys.argv)}")
