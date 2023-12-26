## Env variables
Full list of ``env`` variables and their meaning:
- general:
    - ``task_dir`` - directory being tested
    - ``target`` - what is currently being tested (``all`` / ``solution`` / ``generator``)
    - ``config`` - variables from config
    - ``full`` - If true, don't stop on first failure
    - ``no_colors`` - Don't use ANSI colors
    - ``no_jumps`` - Don't use ANSI cursor movement
    - ``strict`` - For final test. Interprets warning as failures. Currently enforces:
        - There are no TODOs in config
        - Checker exists
    - ``testing_log`` - Create ``testing_log.json`` of the run
    - ``solutions`` - Solutions to test ``pisek`` on. If empty test only generator.
- modifiers:
    - ``timeout`` - Override config timeout for solutions.
    - ``skip_on_timeout`` - Skip testing rest of the subtask's inputs once solution timeouts.
    - ``all_inputs`` - Don't cancel solution on remaining inputs.
    - ``inputs`` - Number of inputs in Kasiopea mode
