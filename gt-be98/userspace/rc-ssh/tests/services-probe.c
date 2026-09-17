/* Exercise the real services.c entry points and manager-only dispatcher. */
#define _GNU_SOURCE
#include "rc-bridge.h"
#include "rc-services.h"
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
void start_cron(void), stop_cron(void), stop_infosvr(void);
int start_infosvr(void), __real_leon_rc_managed(void);
static int legacy, launches, kills;
int __wrap_leon_rc_managed(void) { return legacy ? 0 : __real_leon_rc_managed(); }
int _eval(char *const argv[], const char *path, int timeout, pid_t *ppid)
{
    assert(!path && !timeout);
    if (!strcmp(argv[0], "crond")) {
        assert(!ppid && !strcmp(argv[1], "-l") && !strcmp(argv[2], "9") && !argv[3]);
    } else {
        assert(!strcmp(argv[0], "/usr/sbin/infosvr") && ppid && !strcmp(argv[1], "br0") && !argv[2]);
    }
    launches++; return 0;
}
void killall_tk(const char *name) { assert(!strcmp(name,"crond") || !strcmp(name,"infosvr")); kills++; }
int nvram_get_int(const char *name) { (void)name; return 0; }
int sw_mode(void) { return 1; }
static void shell(const char *s)
{
    char *cmd; assert(asprintf(&cmd,"set -eu; %s",s)>0);
    assert(!leon_rc_system(cmd)); free(cmd);
}
static void mark(const char *s) { puts(s); fflush(stdout); }
static void reap(int sig) { int saved=errno; (void)sig; while(waitpid(-1,NULL,WNOHANG)>0){} errno=saved; }
int main(int argc, char **argv)
{
    sigset_t mask; int status,sig; pid_t child;
    struct sigaction sa={.sa_handler=reap};
    assert(!leon_rc_manager_enter(argc,argv));
    assert(leon_rc_crond(3)==-1 && errno==EINVAL);
    assert(leon_rc_infosvr(-1)==-1 && errno==EINVAL);
    legacy=1; start_cron(); stop_cron(); assert(!start_infosvr()); stop_infosvr();
    assert(launches==2 && kills==3); legacy=0;
    child=fork(); assert(child>=0);
    if(!child) _exit(leon_rc_crond(1)!=-1 || errno!=EPERM || leon_rc_infosvr(1)!=-1 || errno!=EPERM);
    assert(waitpid(child,&status,0)==child && WIFEXITED(status) && !WEXITSTATUS(status));
    sigemptyset(&sa.sa_mask); assert(!sigaction(SIGCHLD,&sa,NULL));
    mark("LAB_MORE_SERVICES_LEGACY_FORK_PASS");
    shell("mkdir -p /var/spool/cron/crontabs; "
          "printf '* * * * * /usr/libexec/cron-child-test\\n' > /var/spool/cron/crontabs/root; "
          "chmod 600 /var/spool/cron/crontabs/root");
    start_cron(); assert(!start_infosvr());
    shell("test \"$(systemctl show asus-rc.service -p ActiveState --value)\" = activating; "
          "for u in crond infosvr; do systemctl is-active --quiet asus-$u.service; "
          "p=$(systemctl show asus-$u.service -p MainPID --value); echo $p > /run/$u-first; "
          "test \"$(awk '/^PPid:/{print $2}' /proc/$p/status)\" = 1; "
          "grep -q '/system.slice/asus-'$u'.service$' /proc/$p/cgroup; done");
    assert(!start_infosvr());
    shell("test \"$(cat /run/infosvr-first)\" = \"$(systemctl show asus-infosvr.service -p MainPID --value)\"; "
          "i=0; until test -s /run/cron-child-pid; do i=$((i+1)); test $i -lt 72; sleep 1; done; "
          "test -d /proc/$(cat /run/cron-child-pid); "
          "grep -q '/system.slice/asus-crond.service$' /proc/$(cat /run/cron-child-pid)/cgroup; "
          "rm /var/spool/cron/crontabs/root");
    start_cron();
    shell("test \"$(cat /run/crond-first)\" != \"$(systemctl show asus-crond.service -p MainPID --value)\"; "
          "test -d /proc/$(cat /run/cron-child-pid); "
          "test ! -e /run/cron-child-terminated");
    mark("LAB_MORE_SERVICES_PRE_READY_AND_CRON_JOB_PRESERVED_PASS");
    shell("for u in crond infosvr; do p=$(systemctl show asus-$u.service -p MainPID --value); "
          "systemctl kill --kill-whom=main --signal=KILL asus-$u.service; i=0; "
          "while :; do n=$(systemctl show asus-$u.service -p MainPID --value); "
          "if test $n -gt 1 && test $n != $p; then break; fi; "
          "i=$((i+1)); test $i -lt 12; sleep 1; done; done");
    stop_cron(); stop_infosvr();
    shell("for u in crond infosvr; do test \"$(systemctl show asus-$u.service -p ActiveState --value)\" = inactive; "
          "! /bin/busybox pidof $u; done; test -d /proc/$(cat /run/cron-child-pid)");
    mark("LAB_MORE_SERVICES_RECOVERY_STOP_PASS");
    shell("for u in crond infosvr; do ln -s /dev/null /run/systemd/system/asus-$u.service; done; systemctl daemon-reload");
    start_cron(); assert(start_infosvr()==-1); stop_cron(); stop_infosvr();
    assert(launches==2 && kills==3);
    shell("rm /run/systemd/system/asus-crond.service /run/systemd/system/asus-infosvr.service; systemctl daemon-reload; "
          "for u in crond infosvr; do ! /bin/busybox pidof $u; done");
    mark("LAB_MORE_SERVICES_FAILURE_NO_FALLBACK_PASS");
    shell("/usr/sbin/crond -l 9; i=0; until /bin/busybox pidof crond > /run/crond-external; do "
          "i=$((i+1)); test $i -lt 10; sleep 1; done; "
          "if systemctl start asus-crond.service; then exit 1; fi; "
          "systemctl stop asus-crond.service; test \"$(/bin/busybox pidof crond)\" = \"$(cat /run/crond-external)\"; "
          "kill $(cat /run/crond-external)");
    sleep(1);
    shell("! /bin/busybox pidof crond; systemctl reset-failed");
    mark("LAB_MORE_SERVICES_DUPLICATE_OWNER_PASS");
    start_cron(); assert(!start_infosvr());
    assert(!leon_rc_ready());
    mark("LAB_MORE_SERVICES_READY_PASS");
    sigemptyset(&mask); sigaddset(&mask,SIGTERM); sigaddset(&mask,SIGQUIT);
    assert(!sigwait(&mask,&sig)); assert(!leon_rc_shutdown_gate(sig==SIGTERM));
    mark("LAB_MORE_SERVICES_DRAIN_PASS"); return 0;
}
