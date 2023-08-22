# Jobs
When testing a task all actions are run inside a pipeline - `JobPipeline`.
`JobPipeline` contains two types of `PipelineItem`s:
 - `Job`s - Actions to be done
 - `JobManger`s - Create jobs and look after them.

## PipelineItem
Both `Job` and `JobManager` share a few common traits.

### Name
Each `PipelineItem` has a name that's displayed to the user.

### State
Each item has a state that represent their progress:
 - `in_queue` - The item is waiting for previous items
 - `running` - The item is running.
 - `succeeded` - The item has successfully ended.
 - `failed` - The item has failed, and the something is wrong with the task being tested.
 - `canceled` - A prerequisite (see below) of this item has failed, therefore this item cannot be run.

### Prerequisites
Each item can have items that must be run before it. (E.g. Running after compilation.) 
Prerequisites must be specified:
 - When creating `Job`s in `JobManager`
 - When creating `JobManager`s in `JobPipeline`'s init.

Additionally each prerequisite must be inserted into the pipeline before the given item.

## Jobs
`Job`s represent a single and simple task.

To decrease run time `Job`'s inputs are monitored, and after `Job` has successfully finished,
it's result is cached. These are all inputs that `Job` can access:
 - `Job._init` parameters
 - `Job._env` variables
 - accessed files - **These are not logged automatically. Every file must passed to `Job._access_file` or accessed by pre-made functions!** Even files we write to must be logged as we need to run the job again if they are deleted.
 - other job's results - Must be added as named prerequisites. 

Next time if `Job` should be run with same inputs, the cached result is used instead.

(Job results are saved in `./.pisek_cache` file.)

### Writing Jobs
A job can look like this (notice things in comments):
```py
class CopyFile(TaskJob): # We inherit from TaskJob, because it provides useful methods
    """Copies a file."""
    def _init(self, source: str, dest: str) -> None:
        self.source = source
        self.dest = dest
        super()._init(f"Copy {source} to {dest}") # Here we give name of the job

    def _run(self):
        if self._env.verbose:  # Accessing a global variable
            print(f"Coping {self.source} to {self.dest}")
            self.dirty = True  # Setting dirty flag because we wrote to a console
        
        shutil.copy(self.source, self.dest)
        self._access_file(self.source)  # Access the source as the result depends on it
        self._access_file(self.dest)  # Also access destination as we need to run the job again if it has changed
        
        # Alternatively we can use `self._copy_file(self.source, self.dest)` with automatic logging
```

Jobs are created this way:
```py
Job(Env).init(*args, **kwargs)
```
1. Env containing global variables is handled separately.
2. `_init` parameters are given to `init` to be logged

## JobManager
Jobs are managed by a `JobManager` in this way:
1. First `JobManager` creates all jobs in `JobManager._get_jobs`.
2. Then repeatedly reports current state of jobs with `JobManager._get_status`.
3. After all jobs have finished, it can check for cross-job failures using `JobManager._evaluate`.

### Writing JobManagers
```py
class ExampleManager(TaskJobManager):  # We inherit from TaskJobManager again for more methods
    def __init__(self):
        super().__init__("Doing something")

    def _get_jobs(self) -> list[Job]:
        # Create list of jobs to run
        jobs : list[Job] = [
            job1 := ExampleJob(self._env).init("1"),
            job2 := ExampleJob(self._env).init("2"),
        ]
        # Add prerequisites accordingly 
        job2.add_prerequisite(job1)

        return jobs
    
    # We don't need to override _get_status as we have a better one already
    # but as an example:
    def _get_status(self) -> str:
        return f"{self.name} {len(self._jobs_with_state(State.succeeded))}/{len(self.jobs)}"

    # Finally we check for cross-job failures
    def _evaluate(self) -> Any:
        if self.jobs[0].result != self.jobs[1].result:
            return self._fail("Both jobs have to have the same result.")
```

## JobPipeline
`JobPipeline` holds all `PipelineItems` and executes them in correct order.

The pipeline has list of `JobManager`s and `Job`s to execute.
Pipeline does the following in each step:
 - If at the top of the pipeline is `JobManager`:
   - Create jobs with it and add them **to the top** of the pipeline.
   - Add this `JobManager` to active ones.
 - If at the top of the pipeline is a `Job`:
    - Run it, or if it's cached use the result
After each step update active `JobManager`s and write current status to console.
