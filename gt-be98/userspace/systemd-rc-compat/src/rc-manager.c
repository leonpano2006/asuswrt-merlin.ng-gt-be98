/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _GNU_SOURCE
#include "rc-bridge.h"
#include <errno.h>
#include <mntent.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <unistd.h>

static pid_t manager_pid;
static int ready_sent;

int leon_rc_manager_enter(int argc, char **argv)
{
    sigset_t mask;
    static const int signals[] = { SIGHUP, SIGINT, SIGQUIT, SIGTERM, SIGUSR1, SIGUSR2 };
    unsigned int i;
    if (!leon_rc_managed()) return getpid() == 1 ? 0 : (errno = EPERM, -1);
    if (leon_rc_preload_ready()) return -1;
    if (argc != 2 || strcmp(argv[1], "--leon-systemd")) { errno = EINVAL; return -1; }
    sigemptyset(&mask);
    for (i=0; i<sizeof(signals)/sizeof(signals[0]); i++) sigaddset(&mask, signals[i]);
    if (sigprocmask(SIG_BLOCK, &mask, NULL) ||
        prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) ||
        leon_rc_exchange(LEON_HELLO, 0, NULL)) return -1;
    manager_pid = getpid();
    return 0;
}

int leon_rc_is_manager(void)
{
    /* A fork child inherits the stored PID, so it does not inherit this role. */
    return getpid() == 1 || (manager_pid > 1 && getpid() == manager_pid);
}

int leon_rc_ready(void)
{
    if (!leon_rc_managed() || ready_sent) return 0;
    if (!leon_rc_is_manager()) { errno = EPERM; return -1; }
    if (leon_rc_exchange(LEON_READY, 0, NULL)) return -1;
    ready_sent = 1;
    return 0;
}

int leon_rc_shutdown_gate(int rebooting)
{
    int stopping = 0, i;
    if (!leon_rc_managed()) return 0;
    if (!leon_rc_is_manager()) { errno = EPERM; return -1; }
    if (leon_rc_exchange(LEON_STATE, 0, &stopping)) return -1;
    if (!stopping && leon_rc_signal(rebooting ? SIGTERM : SIGQUIT)) return -1;
    /* Other units (including USB consumers) stop before the ASUS unit drains. */
    for (i=0; i<120; i++) {
        if (leon_rc_exchange(LEON_STATE, 0, &stopping)) return -1;
        if (stopping) return 0;
        sleep(1);
    }
    errno = ETIMEDOUT;
    return -1;
}

int leon_rc_mount(const char *source, const char *target, const char *type,
                  unsigned long flags, const void *data)
{
    static const char *const protected[] = { "/proc", "/sys", "/dev", "/tmp", "/var", "/run", "/dev/pts", "/dev/shm" };
    unsigned int i;
    if (leon_rc_managed()) for (i=0; i<sizeof(protected)/sizeof(protected[0]); i++) {
        if (!strcmp(target, protected[i])) {
            struct mntent *entry;
            FILE *mounts = setmntent("/proc/self/mounts", "r");
            int found = 0, same = 0;
            if (!mounts) return -1;
            while ((entry = getmntent(mounts))) if (!strcmp(entry->mnt_dir, target)) {
                found = 1;
                same = type && !strcmp(entry->mnt_type, type);
            }
            endmntent(mounts);
            if (found) {
                if (same && !(flags & (MS_REMOUNT | MS_BIND | MS_MOVE))) return 0;
                errno = EBUSY;
                return -1;
            }
        }
    }
    return mount(source, target, type, flags, data);
}
