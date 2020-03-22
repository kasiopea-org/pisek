#!/bin/bash
# Self-tests + formatting (black) + typechecks (mypy)
# Install as a pre-commit hook to check automatically before committing:
# cp check_all.sh .git/hooks/pre-commit

set -e

# Redirect stdout to stderr
exec 2>&1

echo "======== Kontroluji formátování ========"
python3 -m black . --check

echo "======== Kontroluji typy ========"
python3 -m mypy pisek/

echo "======== Testuji ========"
./self_tests.sh
