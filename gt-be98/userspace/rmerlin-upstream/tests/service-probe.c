/* SPDX-License-Identifier: GPL-2.0-or-later */
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

void start_haveged(void);
void stop_haveged(void);
int __real_leon_rc_managed(void);
static int legacy_mode, launches, kills;
int __wrap_leon_rc_managed(void) { return legacy_mode ? 0 : __real_leon_rc_managed(); }

/* Only the unchanged legacy branches use these imports. In managed mode a
 * fallback would increase the counters and fail the test. */
int _eval(char *const argv[], const char *path, int timeout, pid_t *ppid)
{
    const char *expected[] = { "/usr/sbin/haveged", "-r", "0", "-w", "1024", "-d", "32", "-i", "32", NULL };
    unsigned int i;
    assert(!path && !timeout && ppid);
    for (i = 0; expected[i]; i++) assert(argv[i] && !strcmp(argv[i], expected[i]));
    assert(!argv[i]); launches++; return 0;
}
int pids(char *name) { assert(!strcmp(name, "haveged")); return 123; }
void killall_tk(const char *name) { assert(!strcmp(name, "haveged")); kills++; }

static void reaper(int sig)
{
    int saved = errno;
    (void)sig;
    while (waitpid(-1, NULL, WNOHANG) > 0) { }
    errno = saved;
}
static void shell(const char *cmd)
{
    char *strict;
    assert(asprintf(&strict, "set -eu; %s", cmd) > 0);
    assert(leon_rc_system(strict) == 0);
    free(strict);
}
static void mark(const char *s) { puts(s); fflush(stdout); }
static void wait_entropy_loop(void)
{
    /* TCG has no physical CPU jitter. Wait for the real daemon to reach its
     * kernel entropy wait before testing stop, rather than treating exec as
     * completed RNG initialization. Save state if that never happens. */
    shell("p=$(systemctl show asus-haveged.service -p MainPID --value); "
          "i=0; while test \"$(cat /proc/$p/wchan)\" != do_select; do "
          "i=$((i+1)); if test \"$i\" -ge 40; then "
          "cat /proc/$p/status /proc/$p/wchan; journalctl -o cat --no-pager -u asus-haveged.service; exit 1; fi; sleep 1; done; "
          "echo LAB_SERVICE_ENTROPY_WAIT_SECONDS=$i");
}

int main(int argc, char **argv)
{
    sigset_t mask;
    struct sigaction reap = { .sa_handler = reaper };
    pid_t child;
    int status, sig;
    assert(!leon_rc_manager_enter(argc, argv));
    assert(leon_rc_haveged(3) == -1 && errno == EINVAL);
    legacy_mode = 1;
    start_haveged(); stop_haveged();
    assert(launches == 1 && kills == 1);
    legacy_mode = 0;
    child = fork(); assert(child >= 0);
    if (!child) _exit(leon_rc_haveged(1) != -1 || errno != EPERM);
    assert(waitpid(child, &status, 0) == child && WIFEXITED(status) && !WEXITSTATUS(status));
    mark("LAB_SERVICE_LEGACY_AND_FORK_BOUNDARY_PASS");
    sigemptyset(&reap.sa_mask);
    assert(!sigaction(SIGCHLD, &reap, NULL));

    /* A real rc call before READY must not wait for asus-rc.service itself. */
    start_haveged();
    shell("test \"$(systemctl show asus-rc.service -p ActiveState --value)\" = activating; "
          "systemctl is-active --quiet asus-haveged.service; "
          "systemctl show asus-haveged.service -p MainPID --value > /run/haveged-first");
    start_haveged();
    shell("test \"$(cat /run/haveged-first)\" = \"$(systemctl show asus-haveged.service -p MainPID --value)\"; "
          "p=$(cat /run/haveged-first); test \"$(awk '/^PPid:/{print $2}' /proc/$p/status)\" = 1; "
          "grep -q '/system.slice/asus-haveged.service$' /proc/$p/cgroup");
    mark("LAB_SERVICE_BEFORE_READY_SINGLE_OWNER_PASS");
    wait_entropy_loop();
    shell("systemctl kill --kill-whom=main --signal=KILL asus-haveged.service; "
          "i=0; while :; do p=$(systemctl show asus-haveged.service -p MainPID --value); "
          "if test \"$p\" -gt 1 && test \"$p\" != \"$(cat /run/haveged-first)\"; then break; fi; "
          "i=$((i+1)); test \"$i\" -lt 12 || exit 1; sleep 1; done; "
          "test \"$(systemctl show asus-haveged.service -p NRestarts --value)\" -ge 1");
    wait_entropy_loop();
    stop_haveged();
    shell("test \"$(systemctl show asus-haveged.service -p ActiveState --value)\" = inactive; "
          "! /bin/busybox pidof haveged");
    mark("LAB_SERVICE_RECOVERY_AND_EXPLICIT_STOP_PASS");

    shell("ln -s /dev/null /run/systemd/system/asus-haveged.service; systemctl daemon-reload");
    start_haveged(); stop_haveged();
    assert(launches == 1 && kills == 1);
    shell("rm /run/systemd/system/asus-haveged.service; systemctl daemon-reload; "
          "! /bin/busybox pidof haveged");
    mark("LAB_SERVICE_FAILURE_NO_LEGACY_FALLBACK_PASS");

    /* Start the real old daemon once in this offline VM. The unit must refuse
     * it instead of creating two supervisors or killing an external owner. */
    shell("/usr/sbin/haveged -r 0 -w 1024 -d 32 -i 32; "
          "i=0; until /bin/busybox pidof haveged > /run/haveged-external; do "
          "i=$((i+1)); test \"$i\" -lt 10 || exit 1; sleep 1; done; "
          "if systemctl start asus-haveged.service; then exit 1; fi; "
          "systemctl stop asus-haveged.service; "
          "test \"$(/bin/busybox pidof haveged)\" = \"$(cat /run/haveged-external)\"; "
          "p=$(cat /run/haveged-external); i=0; while test \"$(cat /proc/$p/wchan)\" != do_select; do "
          "i=$((i+1)); test \"$i\" -lt 40 || exit 1; sleep 1; done; "
          "kill -TERM $p");
    /* The old detached daemon belongs to this subreaper. Restore/unblock
     * SIGCHLD before waiting for its /proc entry to disappear. */
    sleep(1);
    shell("i=0; while /bin/busybox pidof haveged >/dev/null; do "
          "i=$((i+1)); test \"$i\" -lt 10 || exit 1; sleep 1; done");
    mark("LAB_SERVICE_DUPLICATE_OWNER_REJECTED_PASS");
    start_haveged();
    shell("systemctl is-active --quiet asus-haveged.service");
    wait_entropy_loop();
    assert(launches == 1 && kills == 1);
    assert(!leon_rc_ready());
    mark("LAB_SERVICE_MANAGER_READY_PASS");
    sigemptyset(&mask); sigaddset(&mask, SIGTERM); sigaddset(&mask, SIGQUIT);
    assert(!sigwait(&mask, &sig));
    assert(!leon_rc_shutdown_gate(sig == SIGTERM));
    /* PartOf must stop haveged even if this manager exits without calling its
     * stop function. This also proves the new daemon is outside rc's cgroup. */
    mark("LAB_SERVICE_MANAGER_DRAIN_PASS");
    return 0;
}
