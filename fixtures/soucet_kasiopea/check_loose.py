#!/usr/bin/env python3
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Nacte ze stdin vstupy ulohy a zkontroluje jejich spravnost"
    )
    parser.add_argument("subtask", type=int, help="subtask (indexovany od 1)")
    args = parser.parse_args()

    # Does not do any actual checking.
