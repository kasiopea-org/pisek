/*
 *	This is a stripped-down version of the Isolate sandbox,
 *	which does no real isolation, but still applies resource
 *	limits and kills processes which overstep them.
 *
 *	Of course, this is safe only if the sandboxed program
 *	is not malicious, but it is still a very useful guard
 *	against simple bugs in judges and generators.
 *
 *	See http://github.com/ioi/isolate/ for the original version.
 *
 *	(c) 2012-2017 Martin Mares <mj@ucw.cz>
 *	(c) 2012-2014 Bernard Blackham <bernard@blackham.com.au>
 */

#include <errno.h>
#include <stdio.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdint.h>
#include <unistd.h>
#include <getopt.h>
#include <sched.h>
#include <time.h>
#include <limits.h>
#include <sys/wait.h>
#include <sys/time.h>
#include <sys/signal.h>
#include <sys/resource.h>
#include <sys/stat.h>

#ifdef __APPLE__
#include <crt_externs.h>
#define environ (*_NSGetEnviron())
#endif

#define NONRET __attribute__((noreturn))
#define UNUSED __attribute__((unused))
#define ARRAY_SIZE(a) (int)(sizeof(a)/sizeof(a[0]))

static int timeout;			/* milliseconds */
static int wall_timeout;
static int extra_timeout;
static int pass_environ;
static int verbose;
static int silent;
static int fsize_limit;
static int memory_limit;
static int stack_limit;
static int max_processes = 1;
static char *redir_stdin, *redir_stdout, *redir_stderr;
static int redir_stderr_to_stdout;
static char *set_cwd;

static pid_t box_pid;

static int partial_line;

static struct timeval start_time;
static int ticks_per_sec;
static int total_ms, wall_ms;
static volatile sig_atomic_t timer_tick, interrupt;

static int error_pipes[2];
static int write_errors_to_fd;
static int read_errors_from_fd;

static void die(char *msg, ...) NONRET;
static int get_wall_time_ms(void);
static int get_run_time_ms(struct rusage *rus);

/*** Meta-files ***/

static FILE *metafile;

static void
meta_open(const char *name)
{
  if (!strcmp(name, "-"))
    {
      metafile = stdout;
      return;
    }
  metafile = fopen(name, "w");
  if (!metafile)
    die("Failed to open metafile '%s'",name);
}

static void
meta_close(void)
{
  if (metafile && metafile != stdout)
    fclose(metafile);
}

static void __attribute__((format(printf,1,2)))
meta_printf(const char *fmt, ...)
{
  if (!metafile)
    return;

  va_list args;
  va_start(args, fmt);
  vfprintf(metafile, fmt, args);
  va_end(args);
}

static void
final_stats(struct rusage *rus)
{
  total_ms = get_run_time_ms(rus);
  wall_ms = get_wall_time_ms();

  meta_printf("time:%d.%03d\n", total_ms/1000, total_ms%1000);
  meta_printf("time-wall:%d.%03d\n", wall_ms/1000, wall_ms%1000);
  meta_printf("max-rss:%ld\n", rus->ru_maxrss);
  meta_printf("csw-voluntary:%ld\n", rus->ru_nvcsw);
  meta_printf("csw-forced:%ld\n", rus->ru_nivcsw);
}

/*** Messages and exits ***/

static void NONRET
box_exit(int rc)
{
  if (box_pid > 0)
    {
      kill(-box_pid, SIGKILL);
      kill(box_pid, SIGKILL);
      meta_printf("killed:1\n");

      struct rusage rus;
      int p, stat;
      do
	p = wait4(box_pid, &stat, 0, &rus);
      while (p < 0 && errno == EINTR);
      if (p < 0)
	fprintf(stderr, "UGH: Lost track of the process (%m)\n");
      else
	final_stats(&rus);
    }

  meta_close();
  exit(rc);
}

static void
flush_line(void)
{
  if (partial_line)
    fputc('\n', stderr);
  partial_line = 0;
}

/* Report an error of the sandbox itself */
static void NONRET __attribute__((format(printf,1,2)))
die(char *msg, ...)
{
  va_list args;
  va_start(args, msg);
  char buf[1024];
  int n = vsnprintf(buf, sizeof(buf), msg, args);

  // If the child process is still running, show no mercy.
  if (box_pid > 0)
    {
      kill(-box_pid, SIGKILL);
      kill(box_pid, SIGKILL);
    }

  if (write_errors_to_fd)
    {
      // We are inside the box, have to use error pipe for error reporting.
      // We hope that the whole error message fits in PIPE_BUF bytes.
      write(write_errors_to_fd, buf, n);
      exit(2);
    }

  // Otherwise, we in the box keeper process, so we report errors normally
  flush_line();
  meta_printf("status:XX\nmessage:%s\n", buf);
  fputs(buf, stderr);
  fputc('\n', stderr);
  box_exit(2);
}

/* Report an error of the program inside the sandbox */
static void NONRET __attribute__((format(printf,1,2)))
err(char *msg, ...)
{
  va_list args;
  va_start(args, msg);
  flush_line();
  if (msg[0] && msg[1] && msg[2] == ':' && msg[3] == ' ')
    {
      meta_printf("status:%c%c\n", msg[0], msg[1]);
      msg += 4;
    }
  char buf[1024];
  vsnprintf(buf, sizeof(buf), msg, args);
  meta_printf("message:%s\n", buf);
  if (!silent)
    {
      fputs(buf, stderr);
      fputc('\n', stderr);
    }
  box_exit(1);
}

#if 0
/* Write a message, but only if in verbose mode */
static void __attribute__((format(printf,1,2)))
msg(char *msg, ...)
{
  va_list args;
  va_start(args, msg);
  if (verbose)
    {
      int len = strlen(msg);
      if (len > 0)
        partial_line = (msg[len-1] != '\n');
      vfprintf(stderr, msg, args);
      fflush(stderr);
    }
  va_end(args);
}
#endif

/*** Utility functions ***/

static void *
xmalloc(size_t size)
{
  void *p = malloc(size);
  if (!p)
    die("Out of memory");
  return p;
}

/*** Environment rules ***/

struct env_rule {
  char *var;			// Variable to match
  char *val;			// ""=clear, NULL=inherit
  int var_len;
  struct env_rule *next;
};

static struct env_rule *first_env_rule;
static struct env_rule **last_env_rule = &first_env_rule;

static struct env_rule default_env_rules[] = {
  { .var = "LIBC_FATAL_STDERR_", .val = "1", .var_len = 18 }
};

static int
set_env_action(char *a0)
{
  struct env_rule *r = xmalloc(sizeof(*r) + strlen(a0) + 1);
  char *a = (char *)(r+1);
  strcpy(a, a0);

  char *sep = strchr(a, '=');
  if (sep == a)
    return 0;
  r->var = a;
  if (sep)
    {
      *sep++ = 0;
      r->val = sep;
    }
  else
    r->val = NULL;
  *last_env_rule = r;
  last_env_rule = &r->next;
  r->next = NULL;
  return 1;
}

static int
match_env_var(char *env_entry, struct env_rule *r)
{
  if (strncmp(env_entry, r->var, r->var_len))
    return 0;
  return (env_entry[r->var_len] == '=');
}

static void
apply_env_rule(char **env, int *env_sizep, struct env_rule *r)
{
  // First remove the variable if already set
  int pos = 0;
  while (pos < *env_sizep && !match_env_var(env[pos], r))
    pos++;
  if (pos < *env_sizep)
    {
      (*env_sizep)--;
      env[pos] = env[*env_sizep];
      env[*env_sizep] = NULL;
    }

  // What is the new value?
  char *new;
  if (r->val)
    {
      if (!r->val[0])
	return;
      new = xmalloc(r->var_len + 1 + strlen(r->val) + 1);
      sprintf(new, "%s=%s", r->var, r->val);
    }
  else
    {
      pos = 0;
      while (environ[pos] && !match_env_var(environ[pos], r))
	pos++;
      if (!(new = environ[pos]))
	return;
    }

  // Add it at the end of the array
  env[(*env_sizep)++] = new;
  env[*env_sizep] = NULL;
}

static char **
setup_environment(void)
{
  // Link built-in rules with user rules
  for (int i=ARRAY_SIZE(default_env_rules)-1; i >= 0; i--)
    {
      default_env_rules[i].next = first_env_rule;
      first_env_rule = &default_env_rules[i];
    }

  // Scan the original environment
  char **orig_env = environ;
  int orig_size = 0;
  while (orig_env[orig_size])
    orig_size++;

  // For each rule, reserve one more slot and calculate length
  int num_rules = 0;
  for (struct env_rule *r = first_env_rule; r; r=r->next)
    {
      num_rules++;
      r->var_len = strlen(r->var);
    }

  // Create a new environment
  char **env = xmalloc((orig_size + num_rules + 1) * sizeof(char *));
  int size;
  if (pass_environ)
    {
      memcpy(env, environ, orig_size * sizeof(char *));
      size = orig_size;
    }
  else
    size = 0;
  env[size] = NULL;

  // Apply the rules one by one
  for (struct env_rule *r = first_env_rule; r; r=r->next)
    apply_env_rule(env, &size, r);

  // Return the new env and pass some gossip
  if (verbose > 1)
    {
      fprintf(stderr, "Passing environment:\n");
      for (int i=0; env[i]; i++)
	fprintf(stderr, "\t%s\n", env[i]);
    }
  return env;
}

/*** Signal handling in keeper process ***/

/*
 *   Signal handling is tricky. We must set up signal handlers before
 *   we start the child process (and reset them in the child process).
 *   Otherwise, there is a short time window where a SIGINT can kill
 *   us and leave the child process running.
 */

struct signal_rule {
  int signum;
  enum { SIGNAL_IGNORE, SIGNAL_INTERRUPT, SIGNAL_FATAL } action;
};

static const struct signal_rule signal_rules[] = {
  { SIGHUP,	SIGNAL_INTERRUPT },
  { SIGINT,	SIGNAL_INTERRUPT },
  { SIGQUIT,	SIGNAL_INTERRUPT },
  { SIGILL,	SIGNAL_FATAL },
  { SIGABRT,	SIGNAL_FATAL },
  { SIGFPE,	SIGNAL_FATAL },
  { SIGSEGV,	SIGNAL_FATAL },
  { SIGPIPE,	SIGNAL_IGNORE },
  { SIGTERM,	SIGNAL_INTERRUPT },
  { SIGUSR1,	SIGNAL_IGNORE },
  { SIGUSR2,	SIGNAL_IGNORE },
  { SIGBUS,	SIGNAL_FATAL },
};

static void
signal_alarm(int unused UNUSED)
{
  /* Time limit checks are synchronous, so we only schedule them there. */
  timer_tick = 1;
  alarm(1);
}

static void
signal_int(int signum)
{
  /* Interrupts (e.g., SIGINT) are synchronous, too. */
  interrupt = signum;
}

static void
signal_fatal(int signum)
{
  /* If we receive SIGSEGV or a similar signal, we try to die gracefully */
  die("Sandbox keeper received fatal signal %d", signum);
}

static void
setup_signals(void)
{
  struct sigaction sa_int, sa_fatal;
  bzero(&sa_int, sizeof(sa_int));
  sa_int.sa_handler = signal_int;
  bzero(&sa_fatal, sizeof(sa_fatal));
  sa_fatal.sa_handler = signal_fatal;

  for (int i=0; i < ARRAY_SIZE(signal_rules); i++)
    {
      const struct signal_rule *sr = &signal_rules[i];
      switch (sr->action)
	{
	case SIGNAL_IGNORE:
	  signal(sr->signum, SIG_IGN);
	  break;
	case SIGNAL_INTERRUPT:
	  sigaction(sr->signum, &sa_int, NULL);
	  break;
	case SIGNAL_FATAL:
	  sigaction(sr->signum, &sa_fatal, NULL);
	  break;
	default:
	  die("Invalid signal rule");
	}
    }
}

static void
reset_signals(void)
{
  for (int i=0; i < ARRAY_SIZE(signal_rules); i++)
    signal(signal_rules[i].signum, SIG_DFL);
}

/*** The keeper process ***/

#define PROC_BUF_SIZE 4096
static void
read_proc_file(char *buf, char *name, int *fdp)
{
  int c;

  if (!*fdp)
    {
      sprintf(buf, "/proc/%d/%s", (int) box_pid, name);
      *fdp = open(buf, O_RDONLY);
      if (*fdp < 0)
	die("open(%s): %m", buf);
    }
  lseek(*fdp, 0, SEEK_SET);
  if ((c = read(*fdp, buf, PROC_BUF_SIZE-1)) < 0)
    die("read on /proc/$pid/%s: %m", name);
  if (c >= PROC_BUF_SIZE-1)
    die("/proc/$pid/%s too long", name);
  buf[c] = 0;
}

static int
get_wall_time_ms(void)
{
  struct timeval now, wall;
  gettimeofday(&now, NULL);
  timersub(&now, &start_time, &wall);
  return wall.tv_sec*1000 + wall.tv_usec/1000;
}

static int
get_run_time_ms(struct rusage *rus)
{
  if (rus)
    {
      struct timeval total;
      timeradd(&rus->ru_utime, &rus->ru_stime, &total);
      return total.tv_sec*1000 + total.tv_usec/1000;
    }

  char buf[PROC_BUF_SIZE], *x;
  int utime, stime;
  static int proc_stat_fd;

  read_proc_file(buf, "stat", &proc_stat_fd);
  x = buf;
  while (*x && *x != ' ')
    x++;
  while (*x == ' ')
    x++;
  if (*x++ != '(')
    die("proc stat syntax error 1");
  while (*x && (*x != ')' || x[1] != ' '))
    x++;
  while (*x == ')' || *x == ' ')
    x++;
  if (sscanf(x, "%*c %*d %*d %*d %*d %*d %*d %*d %*d %*d %*d %d %d", &utime, &stime) != 2)
    die("proc stat syntax error 2");

  return (utime + stime) * 1000 / ticks_per_sec;
}

static void
check_timeout(void)
{
  if (wall_timeout)
    {
      int wall_ms = get_wall_time_ms();
      if (wall_ms > wall_timeout)
        err("TO: Time limit exceeded (wall clock)");
      if (verbose > 1)
        fprintf(stderr, "[wall time check: %d msec]\n", wall_ms);
    }
  if (timeout)
    {
      int ms = get_run_time_ms(NULL);
      if (verbose > 1)
	fprintf(stderr, "[time check: %d msec]\n", ms);
      if (ms > timeout && ms > extra_timeout)
	err("TO: Time limit exceeded");
    }
}

static void
box_keeper(void)
{
  read_errors_from_fd = error_pipes[0];
  close(error_pipes[1]);

  gettimeofday(&start_time, NULL);
  ticks_per_sec = sysconf(_SC_CLK_TCK);
  if (ticks_per_sec <= 0)
    die("Invalid ticks_per_sec!");

  if (timeout || wall_timeout)
    {
      struct sigaction sa;
      bzero(&sa, sizeof(sa));
      sa.sa_handler = signal_alarm;
      sigaction(SIGALRM, &sa, NULL);
      alarm(1);
    }

  for(;;)
    {
      struct rusage rus;
      int stat;
      pid_t p;
      if (interrupt)
	{
	  meta_printf("exitsig:%d\n", interrupt);
	  err("SG: Interrupted");
	}
      if (timer_tick)
	{
	  check_timeout();
	  timer_tick = 0;
	}
      p = wait4(box_pid, &stat, 0, &rus);
      if (p < 0)
	{
	  if (errno == EINTR)
	    continue;
	  die("wait4: %m");
	}
      if (p != box_pid)
	die("wait4: unknown pid %d exited!", p);
      box_pid = 0;

      // Check error pipe if there is an internal error passed from inside the box
      char interr[1024];
      int n = read(read_errors_from_fd, interr, sizeof(interr) - 1);
      if (n > 0)
	{
	  interr[n] = 0;
	  die("%s", interr);
	}

      if (WIFEXITED(stat))
	{
	  final_stats(&rus);
	  if (WEXITSTATUS(stat))
	    {
	      meta_printf("exitcode:%d\n", WEXITSTATUS(stat));
	      err("RE: Exited with error status %d", WEXITSTATUS(stat));
	    }
	  if (timeout && total_ms > timeout)
	    err("TO: Time limit exceeded");
	  if (wall_timeout && wall_ms > wall_timeout)
	    err("TO: Time limit exceeded (wall clock)");
	  flush_line();
	  if (!silent)
	    {
	      fprintf(stderr, "OK (%d.%03d sec real, %d.%03d sec wall)\n",
		total_ms/1000, total_ms%1000,
		wall_ms/1000, wall_ms%1000);
	    }
	  box_exit(0);
	}
      else if (WIFSIGNALED(stat))
	{
	  meta_printf("exitsig:%d\n", WTERMSIG(stat));
	  final_stats(&rus);
	  err("SG: Caught fatal signal %d", WTERMSIG(stat));
	}
      else if (WIFSTOPPED(stat))
	{
	  meta_printf("exitsig:%d\n", WSTOPSIG(stat));
	  final_stats(&rus);
	  err("SG: Stopped by signal %d", WSTOPSIG(stat));
	}
      else
	die("wait4: unknown status %x, giving up!", stat);
    }
}

/*** The process running inside the box ***/

static void
setup_credentials(void)
{
  setpgrp();
}

static void
setup_fds(void)
{
  if (redir_stdin)
    {
      close(0);
      if (open(redir_stdin, O_RDONLY) != 0)
	die("open(\"%s\"): %m", redir_stdin);
    }
  if (redir_stdout)
    {
      close(1);
      if (open(redir_stdout, O_WRONLY | O_CREAT | O_TRUNC, 0666) != 1)
	die("open(\"%s\"): %m", redir_stdout);
    }
  if (redir_stderr)
    {
      close(2);
      if (open(redir_stderr, O_WRONLY | O_CREAT | O_TRUNC, 0666) != 2)
	die("open(\"%s\"): %m", redir_stderr);
    }
  if (redir_stderr_to_stdout)
    {
      if (dup2(1, 2) < 0)
	die("Cannot dup stdout to stderr: %m");
    }
}

static void
setup_rlim(const char *res_name, int res, rlim_t limit)
{
  struct rlimit rl = { .rlim_cur = limit, .rlim_max = limit };
  if (setrlimit(res, &rl) < 0)
    die("setrlimit(%s, %jd)", res_name, (intmax_t) limit);
}

static void
setup_rlimits(void)
{
#define RLIM(res, val) setup_rlim("RLIMIT_" #res, RLIMIT_##res, val)

  if (memory_limit)
    RLIM(AS, (rlim_t)memory_limit * 1024);

  if (fsize_limit)
    RLIM(FSIZE, (rlim_t)fsize_limit * 1024);

  RLIM(STACK, (stack_limit ? (rlim_t)stack_limit * 1024 : RLIM_INFINITY));
  RLIM(NOFILE, 64);
  RLIM(MEMLOCK, 0);

  if (max_processes)
    RLIM(NPROC, max_processes);

#undef RLIM
}

static int NONRET
box_inside(void *arg)
{
  char **args = arg;
  write_errors_to_fd = error_pipes[1];
  close(error_pipes[0]);
  meta_close();

  reset_signals();
  setup_credentials();
  setup_fds();
  setup_rlimits();
  char **env = setup_environment();

  if (set_cwd && chdir(set_cwd))
    die("chdir: %m");

  execve(args[0], args, env);
  die("execve(\"%s\"): %m", args[0]);
}

/*** Commands ***/

static void
run(char **argv)
{
  if (pipe(error_pipes) < 0)
    die("pipe: %m");
  for (int i=0; i<2; i++)
    if (fcntl(error_pipes[i], F_SETFD, fcntl(error_pipes[i], F_GETFD) | FD_CLOEXEC) < 0 ||
        fcntl(error_pipes[i], F_SETFL, fcntl(error_pipes[i], F_GETFL) | O_NONBLOCK) < 0)
      die("fcntl on pipe: %m");

  setup_signals();

  box_pid = fork();
  if (box_pid < 0)
    die("clone: %m");
  if (!box_pid)
    box_inside(argv);

  box_keeper();
}

static void
show_version(void)
{
  printf("This is minibox, based on isolate\n");
  printf("(c) 2012-2015 Martin Mares and Bernard Blackham\n");
}

/*** Options ***/

static void __attribute__((format(printf,1,2)))
usage(const char *msg, ...)
{
  if (msg != NULL)
    {
      va_list args;
      va_start(args, msg);
      vfprintf(stderr, msg, args);
      va_end(args);
    }
  printf("\
Usage: minibox [<options>] <command>\n\
\n\
Options:\n\
-c, --chdir=<dir>\tChange directory to <dir> before executing the program\n\
-f, --fsize=<size>\tMax size (in KB) of files that can be created\n\
-E, --env=<var>\t\tInherit the environment variable <var> from the parent process\n\
-E, --env=<var>=<val>\tSet the environment variable <var> to <val>; unset it if <var> is empty\n\
-x, --extra-time=<time>\tSet extra timeout, before which a timing-out program is not yet killed,\n\
\t\t\tso that its real execution time is reported (seconds, fractions allowed)\n\
-e, --full-env\t\tInherit full environment of the parent process\n\
-m, --mem=<size>\tLimit address space to <size> KB\n\
-M, --meta=<file>\tOutput process information to <file> (name:value)\n\
-s, --silent\t\tDo not print status messages except for fatal errors\n\
-k, --stack=<size>\tLimit stack size to <size> KB (default: 0=unlimited)\n\
-r, --stderr=<file>\tRedirect stderr to <file>\n\
    --stderr-to-stdout\tRedirect stderr to stdout\n\
-i, --stdin=<file>\tRedirect stdin from <file>\n\
-o, --stdout=<file>\tRedirect stdout to <file>\n\
-p, --processes[=<max>]\tEnable multiple processes (at most <max> of them)\n\
-t, --time=<time>\tSet run time limit (seconds, fractions allowed)\n\
-v, --verbose\t\tBe verbose (use multiple times for even more verbosity)\n\
-w, --wall-time=<time>\tSet wall clock time limit (seconds, fractions allowed)\n\
\n\
Commands:\n\
    --run -- <cmd> ...\tRun given command within sandbox\n\
    --version\t\tDisplay program version and configuration\n\
");
  exit(2);
}

enum opt_code {
  OPT_VERSION = 256,
  OPT_RUN,
  OPT_STDERR_TO_STDOUT,
};

static const char short_opts[] = "b:c:d:eE:i:k:m:M:o:p::q:r:st:vw:x:";

static const struct option long_opts[] = {
  { "chdir",		1, NULL, 'c' },
  { "fsize",		1, NULL, 'f' },
  { "env",		1, NULL, 'E' },
  { "extra-time",	1, NULL, 'x' },
  { "full-env",		0, NULL, 'e' },
  { "mem",		1, NULL, 'm' },
  { "meta",		1, NULL, 'M' },
  { "processes",	2, NULL, 'p' },
  { "run",		0, NULL, OPT_RUN },
  { "silent",		0, NULL, 's' },
  { "stack",		1, NULL, 'k' },
  { "stderr",		1, NULL, 'r' },
  { "stderr-to-stdout",	0, NULL, OPT_STDERR_TO_STDOUT },
  { "stdin",		1, NULL, 'i' },
  { "stdout",		1, NULL, 'o' },
  { "time",		1, NULL, 't' },
  { "verbose",		0, NULL, 'v' },
  { "version",		0, NULL, OPT_VERSION },
  { "wall-time",	1, NULL, 'w' },
  { NULL,		0, NULL, 0 }
};

int
main(int argc, char **argv)
{
  int c;
  enum opt_code mode = 0;

  while ((c = getopt_long(argc, argv, short_opts, long_opts, NULL)) >= 0)
    switch (c)
      {
      case 'c':
	set_cwd = optarg;
	break;
      case 'f':
        fsize_limit = atoi(optarg);
        break;
      case 'e':
	pass_environ = 1;
	break;
      case 'E':
	if (!set_env_action(optarg))
	  usage("Invalid environment specified: %s\n", optarg);
	break;
      case 'k':
	stack_limit = atoi(optarg);
	break;
      case 'i':
	redir_stdin = optarg;
	break;
      case 'm':
	memory_limit = atoi(optarg);
	break;
      case 'M':
	meta_open(optarg);
	break;
      case 'o':
	redir_stdout = optarg;
	break;
      case 'p':
	if (optarg)
	  max_processes = atoi(optarg);
	else
	  max_processes = 0;
	break;
      case 'r':
	redir_stderr = optarg;
	redir_stderr_to_stdout = 0;
	break;
      case 's':
	silent++;
	break;
      case 't':
	timeout = 1000*atof(optarg);
	break;
      case 'v':
	verbose++;
	break;
      case 'w':
	wall_timeout = 1000*atof(optarg);
	break;
      case 'x':
	extra_timeout = 1000*atof(optarg);
	break;
      case OPT_RUN:
      case OPT_VERSION:
	if (!mode || (int) mode == c)
	  mode = c;
	else
	  usage("Only one command is allowed.\n");
	break;
      case OPT_STDERR_TO_STDOUT:
	redir_stderr = NULL;
	redir_stderr_to_stdout = 1;
	break;
      default:
	usage(NULL);
      }

  if (!mode)
    usage("Please specify a minibox command (e.g. --run).\n");
  if (mode == OPT_VERSION)
    {
      show_version();
      return 0;
    }

  umask(022);

  switch (mode)
    {
    case OPT_RUN:
      if (optind >= argc)
	usage("--run mode requires a command to run\n");
      run(argv+optind);
      break;
    default:
      die("Internal error: mode mismatch");
    }
  exit(0);
}
