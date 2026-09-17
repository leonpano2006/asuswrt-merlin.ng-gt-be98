/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _GNU_SOURCE
#include "rc-bridge.h"
#include "rc-services.h"
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

/* Use fixed service names and argv, clear the child
 * signal mask, and protect waitpid from init.c's SIGCHLD reaper. The unit's
 * JobTimeoutSec bounds the job; this separate deadline bounds its client. */
static int request_unit(const char *unit, int start, int restart)
{
    extern char **environ;
    char *args[] = { "/usr/bin/systemctl", "--no-ask-password", "--no-pager",
                     "--job-mode=fail", NULL, (char *)unit, NULL };
    posix_spawnattr_t attr;
    sigset_t empty, block, previous;
    struct timespec begin, now, pause = { .tv_nsec = 100000000 };
    pid_t pid, waited;
    int error, status = 0;

    if (start != 0 && start != 1) { errno = EINVAL; return -1; }
    if (!leon_rc_managed()) return 0;
    if (geteuid() != 0 || !leon_rc_is_manager()) { errno = EPERM; return -1; }
    args[4] = start ? (restart ? "restart" : "start") : "stop";
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

int leon_rc_haveged(int start)
{
    return request_unit("asus-haveged.service", start, 0);
}

int leon_rc_crond(int start)
{
    /* ASUS start_cron() also refreshes the daemon after timezone changes. */
    return request_unit("asus-crond.service", start, 1);
}

int leon_rc_infosvr(int start)
{
    return request_unit("asus-infosvr.service", start, 0);
}

/* Preserve ASUS's argv construction without a shell or systemd expansion.
 * The broker owns /run/leon-rc (root:0700); rename publishes complete argv
 * for initial launch and later supervisor restarts. Nothing persists to USB. */
static int configured_unit(const char *name, const char *unit, int start,
                           char *const argv[], int restart)
{
    char path[96], temporary[112], data[8192];
    size_t size = 0, len, offset;
    int fd, error = 0, i;
    ssize_t written;

    if (start != 0 && start != 1) { errno = EINVAL; return -1; }
    if (!leon_rc_managed()) return 0;
    if (geteuid() != 0 || !leon_rc_is_manager()) { errno = EPERM; return -1; }
    if (!start) return request_unit(unit, 0, restart);
    if (!argv || !argv[0]) { errno = EINVAL; return -1; }
    for (i = 0; argv[i]; i++) {
        if (i >= 31) { errno = E2BIG; return -1; }
        len = strnlen(argv[i], sizeof(data) - size);
        if (len >= sizeof(data) - size) { errno = E2BIG; return -1; }
        memcpy(data + size, argv[i], len + 1);
        size += len + 1;
    }
    snprintf(path, sizeof(path), "/run/leon-rc/%s.argv", name);
    snprintf(temporary, sizeof(temporary), "%s.XXXXXX", path);
    fd = mkostemp(temporary, O_CLOEXEC);
    if (fd < 0) return -1;
    for (offset = 0; offset < size; offset += written) {
        written = write(fd, data + offset, size - offset);
        if (written < 0 && errno == EINTR) { written = 0; continue; }
        if (written <= 0) { error = written ? errno : EIO; break; }
    }
    if (close(fd) && !error) error = errno;
    if (!error && rename(temporary, path)) error = errno;
    if (error) { unlink(temporary); errno = error; return -1; }
    return request_unit(unit, 1, restart);
}

int leon_rc_mdns(int start, char *const argv[])
{
    return configured_unit("mdns", "asus-mdns.service", start, argv, 0);
}

int leon_rc_ntpd(int start, char *const argv[])
{
    return configured_unit("ntpd", "asus-ntpd.service", start, argv, 1);
}

int leon_rc_sshd(int start, char *const argv[])
{
    /* ASUS applies SSH setting changes through stop_sshd()/start_sshd().
     * Repeated starts must not disconnect established sessions. */
    return configured_unit("sshd", "asus-sshd.service", start, argv, 0);
}
