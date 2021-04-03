#!/usr/bin/env python3
# Checker based on Kasiopea's checker template from Pali Madaj.
import sys
import argparse


def main(diff):
    # Here BOUNDS[2] are stricter than what the generator really creates.
    BOUNDS = [(0, 1e9), (-1e9, 1e9), (-1e9, 1e9)]
    read_values(2, *BOUNDS[diff])


# ----------------- Cast nize jsou pomocne funkce, snad nebude treba upravovat -----------------

line_number = 0


def read_line():
    global line_number
    line_number += 1
    return input()


def fail(message):
    global line_number
    print(message + " (na radku {})".format(line_number), file=sys.stderr)
    sys.exit(1)


def read_values(count=None, minimum=None, maximum=None, value_type=int):
    try:
        line = read_line()
    except EOFError:
        fail("Konec souboru.")

    try:
        numbers = list(map(value_type, line.split(" ")))
    except ValueError:
        fail("Hodnota neni typu {}.".format(value_type))

    if count is not None and len(numbers) != count:
        fail("Pocet hodnot na radku byl {} a mel byt {}.".format(len(numbers), count))
    if minimum is not None and any(x < minimum for x in numbers):
        fail("Nejaka hodnota na radku byla mensi nez {}.".format(minimum))
    if maximum is not None and any(x > maximum for x in numbers):
        fail("Nejaka hodnota na radku byla vetsi nez {}.".format(maximum))

    return numbers


def expect_eof():
    koniec = False
    try:
        input()
    except EOFError:
        koniec = True
    if not koniec:
        fail("Soubor pokracuje, ale mel uz skoncit.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Nacte ze stdin vstupy ulohy a zkontroluje jejich spravnost"
    )
    parser.add_argument("subtask", type=int, help="subtask (indexovany od 1)")
    args = parser.parse_args()
    main(args.subtask - 1)
    expect_eof()
