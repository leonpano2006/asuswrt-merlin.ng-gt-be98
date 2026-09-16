/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _GNU_SOURCE
#include "rc-bridge.h"
#include <assert.h>
#include <signal.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

/* This regression isolates the real manager entry signal mask. No router I/O. */
int leon_rc_managed(void) { return 1; }
int leon_rc_preload_ready(void) { return 0; }
int leon_rc_exchange(unsigned int op, int value, int *result)
{ (void)op; (void)value; (void)result; return 0; }
int leon_rc_signal(int sig) { (void)sig; return 0; }
static void reaped(int sig) { (void)sig; raise(SIGALRM); }

int main(void)
{
    pid_t p = fork();
    int status;
    assert(p >= 0);
    if (!p) {
        char *args[] = { "/sbin/init", "--leon-systemd", NULL };
        sigset_t pending, alarm;
        int caught;
        assert(!leon_rc_manager_enter(2, args));
        assert(signal(SIGCHLD, reaped) != SIG_ERR);
        /* init.c installs handle_reap before its later initsigs blocking. */
        assert(!raise(SIGCHLD));
        assert(!sigpending(&pending) && sigismember(&pending, SIGALRM));
        sigemptyset(&alarm); sigaddset(&alarm, SIGALRM);
        assert(!sigwait(&alarm, &caught) && caught == SIGALRM);
        _exit(0);
    }
    assert(waitpid(p, &status, 0) == p);
    printf("manager_exit=%d manager_signal=%d\n",
           WIFEXITED(status) ? WEXITSTATUS(status) : -1,
           WIFSIGNALED(status) ? WTERMSIG(status) : 0);
    return !(WIFEXITED(status) && !WEXITSTATUS(status));
}
