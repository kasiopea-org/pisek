## Env variables
Full list of ``env`` variables and their meaning:
- general:
    - ``task_dir`` - directory being tested
    - ``target`` - what is currently being tested (``all`` / ``solution`` / ``generator``)
    - ``config`` - variables from config
    - ``full`` - If true, don't stop on first failure
    - ``strict`` - For final test. Interprets warning as failures. Currently enforces:
        - There are no TODOs in config
        - Checker exists
    - ``solutions`` - Solutions to test ``pisek`` on. If empty test only generator.
- modifiers:
    - ``timeout`` - Override config timeout for solutions.
    - ``skip_on_timeout`` - Skip testing rest of the subtask's inputs once solution timeouts.
    - ``all_inputs`` - Don't cancel solution on remaining inputs.
    - ``inputs`` - Number of inputs in Kasiopea mode
