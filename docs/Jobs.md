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
TODO
