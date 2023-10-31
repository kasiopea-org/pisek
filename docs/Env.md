## Env variables
Full list of ``env`` variables and their meaning:
- ``task_dir`` - directory being tested
- ``config`` - variables from config
- ``full`` - If true, don't stop on first failure
- ``strict`` - For final test. Interprets warning as failures. Currently enforces:
    - There are no TODOs in config
    - Checker exists
- ``solutions`` - Solutions to test ``pisek`` on. If empty test only generator.
- ``timeout`` - Override config timeout for solutions.
- ``inputs`` - Number of inputs in Kasiopea mode
