/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _GNU_SOURCE
#include "rc-bridge.h"
#include "rc-services.h"
#include <errno.h>
#include <signal.h>
#include <spawn.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

/* Only this service is delegated in phase 1. Use fixed argv, clear the child
 * signal mask, and protect waitpid from init.c's SIGCHLD reaper. The unit's
 * JobTimeoutSec bounds the job; this separate deadline bounds its client. */
int leon_rc_haveged(int start)
{
    extern char **environ;
    char *args[] = { "/usr/bin/systemctl", "--no-ask-password", "--no-pager",
                     "--job-mode=fail", NULL, "asus-haveged.service", NULL };
    posix_spawnattr_t attr;
    sigset_t empty, block, previous;
    struct timespec begin, now, pause = { .tv_nsec = 100000000 };
    pid_t pid, waited;
    int error, status = 0;

    if (start != 0 && start != 1) { errno = EINVAL; return -1; }
    if (!leon_rc_managed()) return 0;
    if (geteuid() != 0 || !leon_rc_is_manager()) { errno = EPERM; return -1; }
    args[4] = start ? "start" : "stop";
    if (clock_gettime(CLOCK_MONOTONIC, &begin)) return -1;
    sigemptyset(&empty);
    sigemptyset(&block); sigaddset(&block, SIGCHLD);
    error = posix_spawnattr_init(&attr);
    if (error) { errno = error; return -1; }
    error = posix_spawnattr_setsigmask(&attr, &empty);
    if (!error) error = posix_spawnattr_setflags(&attr, POSIX_SPAWN_SETSIGMASK);
    if (error) { posix_spawnattr_destroy(&attr); errno = error; return -1; }
    if (sigprocmask(SIG_BLOCK, &block, &previous)) {
        error = errno; posix_spawnattr_destroy(&attr); errno = error; return -1;
    }
    error = posix_spawn(&pid, args[0], NULL, &attr, args, environ);
    posix_spawnattr_destroy(&attr);
    if (!error) for (;;) {
        waited = waitpid(pid, &status, WNOHANG);
        if (waited == pid) {
            if (!WIFEXITED(status) || WEXITSTATUS(status)) error = EIO;
            break;
        }
        if (waited < 0 && errno != EINTR) { error = errno; break; }
        if (clock_gettime(CLOCK_MONOTONIC, &now)) error = errno;
        else if (now.tv_sec - begin.tv_sec >= 30) error = ETIMEDOUT;
        if (error) {
            /* Only reap/kill the systemctl child created by this call. */
            kill(pid, SIGKILL);
            do { waited = waitpid(pid, &status, 0); } while (waited < 0 && errno == EINTR);
            break;
        }
        nanosleep(&pause, NULL);
    }
    if (sigprocmask(SIG_SETMASK, &previous, NULL) && !error) error = errno;
    if (error) { errno = error; return -1; }
    return 1;
}
