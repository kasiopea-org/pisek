# CMS Integration

Pisek can automatically import tasks into the [Contest Management System](https://cms-dev.github.io/)
used at the [International Olympiad in Informatics](https://ioinformatics.org/).
Additionally, it can submit reference solutions as a test user
and verify that all of them score as expected.

## Setup

To import tasks, Pisek calls into CMS's internal libraries.
Therefore, CMS and Pisek have to be installed in the same Python environment,
be it both globally or in the same [virtual environment](https://docs.python.org/3/library/venv.html).
You can either install Pisek onto one of the servers hosting CMS,
or you can install both onto a separate computer.

Installing Pisek and CMS together is no easy feat.
CMS only supports Python up to version 3.9, while Pisek requires Python 3.11.
Getting CMS to work in Python 3.11 requires updating some dependencies
and making a few small changes to its source code to work around
breaking changes in Python's standard libraries.
For details, refer to the provided Dev Container Dockerfile.

Additionally, you will need to provide a `cms.conf` config file.
Pisek uses CMS's utilities to locate it, so using it on a CMS server will require no further setup.
The config file should be located at `/etc/cms.conf` or `/usr/local/etc/cms.conf`.
You can also specify the path to the config file using the `CMS_CONFIG` environment variable.

## Configuration

When importing into CMS, Pisek will use the same configuration as it uses during testing.
However, there are some options are specific to importing into CMS.
These reside in the `[cms]` section of the config file and are all optional.
However, there are a couple of options that you'll probably want to change:

```ini
[cms]
title=Rabbit pathfinding # The display name of the task
time_limit=1.5 # The time limit, in seconds
mem_limit=512 # The memory limit, in mebibytes
```

For details on other options, see the example config.

## Importing and managing tasks

Tasks in CMS consist of two main parts: The task itself and its datasets.
Contests don't always go as planned, which is why CMS allows changing testcases,
output judges, time and memory limits and similar values on the fly.
This is handled through datasets.
When a change is needed, the organisers can create a new, hidden dataset with the given change,
automatically re-evaluate all submissions in the background and finally atomically swap the datasets out.
Some settings are stored in the task itself and cannot be changed using datasets.
This includes the tasks name, the maximum number of submissions,
or the number of decimal digits in scores.

For more information on CMS tasks, see [the documentation](https://cms.readthedocs.io/en/latest/index.html).

Pisek allows you to manage both parts independently.

### Creating a new task

Before anything else can be done, a task must be created in CMS.
To do that, use the `create` subcommand of the `cms` module:

```sh
pisek cms create
```

This will first not only create a task with all the values specified in the task config,
but it will also create the first dataset.
It will also run and test the primary solution first, to generate inputs and outputs.

The new task won't be part of any contest.
To assign it to a contest, use the Admin Web Server.

The description of the initial dataset can be changed using the `--description` or `-d` option:

```sh
pisek cms create -d "My first dataset"
```


### Adding a dataset

If you need to change testcases, judges, stubs, managers or resource limits
before or during the contest, you need to create a new dataset.
The `add` command allows you to just that:

```sh
pisek cms add
```

This will run the primary solution again, if needed, to generate new inputs and outputs.
It will then upload them to the CMS and create a new dataset.

Note that this will **not update the task's properties**.
The only values from the `[cms]` section of the config file that have any effect
are `time_limit` and `mem_limit`.
To update the remaining options, use `pisek cms update`.

This dataset won't be live, but it will be judged automatically in the background.
If you don't want all submissions to be judged on this dataset automatically,
you can use the `--no-autojudge` option:

```sh
pisek cms add --no-autojudge"
```

To make a dataset live, use the Admin Web Server.
The task page will contain a "[Make live ...]" button next above the dataset configuration.

The description of the dataset can be specified using the `--description` or `-d` option:

```sh
pisek cms add -d "Better dataset"
```

By default, the description will be set to the current date and time.

### Updating the settings of a task

The `update` command allows you to update the task's settings:

```sh
pisek cms update
```

This will change the task's properties to match those
defined in the `[cms]` section of the config file.
Note that this will **not create a new dataset**.
The `time_limit` and `mem_limit` options won't be updated,
as those are stored inside datasets.

## Submitting reference solutions

Since most task authors don't develop tasks on the machines used to host CMS's workers,
it's important to try and evaluate reference solutions with CMS.
Additionally, there are some differences between how CMS and Pisek executes programs.

Before any submissions can be made, the tested task needs to be assigned to a contest.
Since all submissions must be associated with a user,
a testing user needs to be created and added to contest as well.
It's recommended to mark the user's participation as hidden,
as this will prevent it from showing up in the scoreboard.

### Submitting

To submit all reference solutions, simply use the `submit` command:

```sh
pisek cms submit -u [user]
```

Set the `-u`/`--username` argument to the username of the test user.

It might take a while before the Evaluation Service notices the new submissions and starts evaluating them.
To speed this process up, you can use the reevaluation buttons in the Admin Web Server,
but make sure not to reevaluate more than what you want.

The `submit` command checks which solutions have already been submitted, and won't submit them again.

### Checking the results

Once the submissions have finished evaluating, you can check the results with the `check` command:

```sh
pisek cms check -d [dataset]
```

Set the `-d`/`--dataset` argument to the description of the dataset you're interested in.

This will print out how many points each solution received, as well as how well it did on each subtask:

```
solve_fast: 100.0 points
  Samples: 1.0
  Subtask 1: 1.0
  Subtask 2: 1.0
solve_slow: 60.0 points (should be 0)
  Samples: 1.0
  Subtask 1: 1.0 (should be wrong)
  Subtask 2: 0.0
```

Any result that doesn't match the constraints defined in the config file will be highlighted in red.

Note that CMS doesn't differentiate between wrong answers and timeouts or runtime errors,
so any error will be reported as "wrong".

### Generating a testing log

You can also generate a JSON file with details on how each solution did on each testcase.
To do that, simply use the `testing-log` command:

```sh
pisek cms testing-log -d [dataset]
```

Again, set the `-d`/`--dataset` argument to the description of the target dataset.

The format is compatible with the file generated when running Pisek with the `--testing-log` argument.
Note that if the submission failed for any reason, the `result` key will be set to `wrong_answer`,
even if the submission timed out or crashed.
