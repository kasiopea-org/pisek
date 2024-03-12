#!/bin/bash
# Self-tests + formatting (black) + typechecks (mypy)
# Install as a pre-commit hook to check automatically before committing:
# ln -s ../check_all.sh .git/hooks/pre-commit

set -e

# Redirect stdout to stderr
exec 2>&1

echo "======== Checking formatting ========"
python3 -m black . --check

echo "======== Checking types ========"
python3 -m mypy pisek/

echo "======== Testing ========"
./tests.sh
