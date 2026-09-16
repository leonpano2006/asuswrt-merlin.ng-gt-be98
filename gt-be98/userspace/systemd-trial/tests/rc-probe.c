/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _GNU_SOURCE
#include "rc-bridge.h"
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mount.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>
int commit(int, char *);
int setBootImageState(int);

static void early_reap(int sig) { (void)sig; raise(SIGALRM); }

static void put(const char *name, int value)
{
    char path[160]; FILE *file;
    snprintf(path,sizeof(path),"/run/%s",name);
    file=fopen(path,"w"); assert(file); fprintf(file,"%d\n",value); assert(!fclose(file));
}

int main(int argc, char **argv)
{
    sigset_t mask;
    int signal, status, notifications=0;
    pid_t p;
    char flag='1';
    assert(getpid() > 1 && getpid() == syscall(SYS_getpid));
    assert(!leon_rc_is_manager());
    assert(!leon_rc_manager_enter(argc,argv));
    assert(leon_rc_is_manager());
    {
        sigset_t pending, alarm;
        struct sigaction action = { .sa_handler = early_reap }, previous;
        sigemptyset(&action.sa_mask);
        assert(!sigaction(SIGCHLD, &action, &previous));
        assert(!raise(SIGCHLD));
        assert(!sigpending(&pending) && sigismember(&pending, SIGALRM));
        sigemptyset(&alarm); sigaddset(&alarm, SIGALRM);
        assert(!sigwait(&alarm, &signal) && signal == SIGALRM);
        /* Restore before the existing child/subreaper regression checks. */
        assert(!sigaction(SIGCHLD, &previous, NULL));
        puts("LAB_RC_EARLY_SIGCHLD_ALARM_PASS");
    }
    assert(leon_rc_system("/usr/libexec/signal-mask-probe") == 0);
    assert(leon_rc_system("/usr/libexec/notify-probe --early") == 0);
    {
        sigset_t pending, startup;
        assert(!sigpending(&pending) && sigismember(&pending, SIGUSR1));
        sigemptyset(&startup); sigaddset(&startup, SIGUSR1);
        assert(!sigwait(&startup, &signal) && signal == SIGUSR1);
        unlink("/run/asus-test-nvram/rc_service");
    }
    puts("LAB_RC_BSP_SIGNAL_MASK_PASS");
    assert(!getenv("LD_PRELOAD"));
    assert(commit(1,&flag)==-1 && setBootImageState(0)==-1);
    p=fork();assert(p>=0);
    if (!p) _exit(leon_rc_is_manager() || getpid()!=syscall(SYS_getpid));
    assert(waitpid(p,&status,0)==p && WIFEXITED(status) && WEXITSTATUS(status)==0);
    /* The real manager helper reaps a daemon double-fork as a subreaper. */
    p=fork();assert(p>=0);
    if (!p) { pid_t grandchild=fork(); if (grandchild < 0) _exit(1); if (!grandchild) { usleep(100000); _exit(23); } _exit(0); }
    assert(waitpid(p,&status,0)==p && WIFEXITED(status) && !WEXITSTATUS(status));
    assert(waitpid(-1,&status,0)>0 && WIFEXITED(status) && WEXITSTATUS(status)==23);
    assert(!leon_rc_mount("tmpfs","/tmp","tmpfs",0,NULL));
    assert(leon_rc_mount("tmpfs","/tmp","proc",0,NULL)==-1 && errno==EBUSY);
    assert(access("/tmp/etc/systemd/system.conf",F_OK)==0);
    put("rc-probe-pid",getpid());
    puts("LAB_RC_IDENTITY_GUARD_SUBREAPER_MOUNTS_PASS");fflush(stdout);
    assert(!leon_rc_ready());
    sigemptyset(&mask);
    sigaddset(&mask,SIGUSR1);sigaddset(&mask,SIGUSR2);sigaddset(&mask,SIGHUP);
    sigaddset(&mask,SIGINT);sigaddset(&mask,SIGTERM);sigaddset(&mask,SIGQUIT);
    for (;;) {
        assert(!sigwait(&mask,&signal));
        if (signal==SIGTERM || signal==SIGQUIT) {
            assert(!leon_rc_shutdown_gate(signal==SIGTERM));
            put("rc-probe-drained",signal);
            puts("LAB_RC_ORDERED_DRAIN_PASS");fflush(stdout);
            return 0;
        }
        if (signal==SIGUSR1) {
            unlink("/run/asus-test-nvram/rc_service");
            put("rc-probe-notifications",++notifications);
        } else put("rc-probe-state",signal);
    }
}
