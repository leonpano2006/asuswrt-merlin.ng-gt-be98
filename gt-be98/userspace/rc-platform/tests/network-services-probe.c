/* Test real services.o and ntpd.o against only NVRAM/hardware side-effect stubs. */
#define _GNU_SOURCE
#include "rc-bridge.h"
#include "rc-services.h"
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

int start_mdns(void), start_ntpd(void), ntpd_synced_main(int,char **);
void stop_mdns(void), restart_mdns(void), stop_ntpd(void);
int __real_leon_rc_managed(void);
static int legacy, launches, kills, notified, ready, effects, verbose, server;
int __wrap_leon_rc_managed(void) { return legacy ? 0 : __real_leon_rc_managed(); }
char *nvram_get(const char *name)
{
    if (!strcmp(name,"ntp_server0")) return "127.0.0.2";
    if (!strcmp(name,"ntp_server1")) return "127.0.0.3";
    if (!strcmp(name,"lan_ifname")) return "lo";
    if (!strcmp(name,"ntp_ready")) return ready ? "1" : "0";
    return "";
}
int nvram_get_int(const char *name)
{
    if (!strcmp(name,"ava_verb")) return verbose;
    if (!strcmp(name,"ntpd_enable")) return server;
    return atoi(nvram_get(name));
}
int nvram_set(const char *name,const char *value)
{ if (!strcmp(name,"ntp_ready")) ready=atoi(value); return 0; }
int nvram_set_int(const char *name,int value) { (void)name;(void)value;return 0; }
int notify_rc(const char *event)
{
    if (!strcmp(event,"restart_diskmon")) { assert(leon_rc_is_manager());return 0; }
    assert(!leon_rc_is_manager());
    if (!strcmp(event,"start_mdns")) notified|=1;
    else if (!strcmp(event,"stop_mdns")) notified|=2;
    else if (!strcmp(event,"start_mdns_refresh")) notified|=4;
    else if (!strcmp(event,"start_ntpd_synced")) notified|=8;
    else if (!strcmp(event,"start_ntpd")) notified|=16;
    else if (!strcmp(event,"stop_ntpd")) notified|=32;
    else abort();
    return 0;
}
int _eval(char *const argv[], const char *path, int timeout, pid_t *pid)
{
    assert(!path && !timeout && pid);
    if (!strcmp(argv[0],"avahi-daemon")) assert(!strcmp(argv[1],"-D"));
    else { assert(!strcmp(argv[0],"/usr/sbin/ntp")); for(int i=1;argv[i];i++) assert(strcmp(argv[i],"-n")); }
    launches++;return 0;
}
void killall_tk(const char *name) { assert(!strcmp(name,"ntp")); kills++; }
int killall(const char *name,int sig) { (void)name;(void)sig;abort(); }
void cprintf(const char *fmt,...) { (void)fmt; }
int pids(const char *name) { return legacy && !strcmp(name,"ntp"); }
char *get_lan_hostname(void) { return "leon-qemu"; }
char *get_productid(void) { return "GT-BE98"; }
int is_valid_hostname(const char *name) { return *name!=0; }
int f_exists(const char *name) { return access(name,F_OK)==0; }
void mkdir_if_none(const char *name) { assert(!mkdir(name,0755) || errno==EEXIST); }
void append_custom_config(const char *name, FILE *f) { (void)name;(void)f; }
void use_custom_config(const char *name, const char *path) { (void)name;(void)path; }
void run_postconf(const char *name, const char *path) { (void)name;(void)path; }
void logmessage_normal(const char *name,const char *fmt,...) { (void)name;(void)fmt; }
void exec_uu(void) { assert(leon_rc_is_manager()); }
void stop_diskmon(void) { assert(leon_rc_is_manager()); }
void start_diskmon(void) { assert(leon_rc_is_manager()); }
void __wrap_stop_stubby(void) { abort(); }
void __wrap_start_stubby(void) { abort(); }
void __wrap_stop_ddns(void) { assert(leon_rc_is_manager()); effects++; }
int __wrap_start_ddns(char *caller,int aidisk) { assert(!caller && !aidisk && leon_rc_is_manager());effects++;return 0; }
void start_ovpn_eas(void) { assert(leon_rc_is_manager());effects++; }
void setup_timezone(void) { assert(leon_rc_is_manager()); }
void timecheck(void) { assert(leon_rc_is_manager()); }
void update_ntp_ts(long before,long delta) { (void)delta;assert(before>0); }
int pidof(const char *name) { (void)name;return -1; }
void kill_pidfile_s(const char *path,int sig) { (void)path;(void)sig;abort(); }
static void shell(const char *s)
{
    char *cmd; assert(asprintf(&cmd,"set -eu; %s",s)>0);
    assert(!leon_rc_system(cmd)); free(cmd);
}
static void mark(const char *s) { puts(s);fflush(stdout); }
static void reap(int sig) { int e=errno;(void)sig;while(waitpid(-1,NULL,WNOHANG)>0){}errno=e; }
int main(int argc,char **argv)
{
    int status,sig;pid_t child;sigset_t mask;
    struct sigaction sa={.sa_handler=reap};
    char *step[]={"ntpd_synced","step",NULL};
    char *periodic[]={"ntpd_synced","periodic",NULL};
    assert(!leon_rc_manager_enter(argc,argv));
    umask(0); /* Match init.c's sysinit, after the broker's private umask. */
    legacy=1;assert(!start_mdns());stop_mdns();assert(!start_ntpd());stop_ntpd();
    assert(launches==2 && kills==1);legacy=0;
    child=fork();assert(child>=0);
    if(!child) {
        assert(leon_rc_mdns(1,NULL)==-1 && errno==EPERM);
        assert(leon_rc_ntpd(1,NULL)==-1 && errno==EPERM);
        assert(!start_mdns());stop_mdns();restart_mdns();
        assert(!ntpd_synced_main(2,step));assert(!ntpd_synced_main(2,periodic));
        assert(!start_ntpd());stop_ntpd();
        _exit(notified!=63 || effects!=0 || ready!=0);
    }
    assert(waitpid(child,&status,0)==child && WIFEXITED(status) && !WEXITSTATUS(status));
    mark("LAB_NETWORK_SERVICES_LEGACY_CHILD_ROUTING_PASS");
    sigemptyset(&sa.sa_mask);assert(!sigaction(SIGCHLD,&sa,NULL));
    verbose=1;server=1;
    assert(!start_mdns());assert(!start_ntpd());
    shell("test $(systemctl show asus-rc.service -p ActiveState --value) = activating; "
          "/usr/libexec/check-network-daemons; "
          "grep -q 'host-name=leon-qemu' /tmp/avahi/avahi-daemon.conf");
    assert(!ntpd_synced_main(2,step));assert(ready==1 && effects==3);
    assert(!ntpd_synced_main(2,step));assert(effects==3);
    mark("LAB_NETWORK_SERVICES_PRE_READY_CONFIG_CALLBACK_PASS");
    /* A daemon-only restart must not affect a process launched by rc. */
    shell("sleep 300 & echo $! > /run/rc-independent-child; "
          "for u in mdns ntpd; do systemctl show asus-$u.service -p MainPID --value > /run/$u-first; done");
    assert(!start_mdns());
    shell("test $(cat /run/mdns-first) = $(systemctl show asus-mdns.service -p MainPID --value)");
    restart_mdns();
    shell("test $(cat /run/mdns-first) = $(systemctl show asus-mdns.service -p MainPID --value); "
          "test -r /tmp/avahi/services/mt-daap.service");
    verbose=0;server=0;
    stop_mdns();assert(!start_mdns());assert(!start_ntpd());
    shell("for u in mdns ntpd; do test $(cat /run/$u-first) != $(systemctl show asus-$u.service -p MainPID --value); done; "
          "/usr/libexec/check-network-daemons client; "
          "test -d /proc/$(cat /run/rc-independent-child)");
    shell("for u in mdns ntpd; do p=$(systemctl show asus-$u.service -p MainPID --value); "
          "systemctl kill --kill-whom=main --signal=KILL asus-$u.service; i=0; "
          "while :; do n=$(systemctl show asus-$u.service -p MainPID --value); "
          "if test $n -gt 1 && test $n != $p; then break; fi; "
          "i=$((i+1)); test $i -lt 12; sleep 1; done; done; /usr/libexec/check-network-daemons client");
    stop_mdns();stop_ntpd();
    shell("for u in mdns ntpd; do test $(systemctl show asus-$u.service -p ActiveState --value) = inactive; done; "
          "! /bin/busybox pidof avahi-daemon; ! /bin/busybox pidof ntp; "
          "test -d /proc/$(cat /run/rc-independent-child); kill $(cat /run/rc-independent-child)");
    mark("LAB_NETWORK_SERVICES_RECONFIGURE_RECOVERY_ISOLATION_PASS");
    shell("for pair in mdns:avahi-daemon ntpd:ntp; do u=${pair%:*}; name=${pair#*:}; "
          "/usr/libexec/leon-service-exec $u & outsider=$!; i=0; "
          "until test \"$(/bin/busybox pidof $name)\" = $outsider; do "
          "i=$((i+1)); test $i -lt 10; sleep 1; done; "
          "if systemctl start asus-$u.service; then exit 1; fi; "
          "systemctl stop asus-$u.service; test -d /proc/$outsider; kill $outsider; wait $outsider || :; done; "
          "systemctl reset-failed");
    assert(leon_rc_ntpd(1,NULL)==-1 && errno==EINVAL);
    shell("cp /run/leon-rc/ntpd.argv /run/ntpd-args-saved; "
          "chmod 666 /run/leon-rc/ntpd.argv; "
          "if /usr/libexec/leon-service-exec ntpd; then exit 1; fi; "
          "chmod 600 /run/leon-rc/ntpd.argv; printf bad > /run/leon-rc/ntpd.argv; "
          "if /usr/libexec/leon-service-exec ntpd; then exit 1; fi; "
          "mv /run/ntpd-args-saved /run/leon-rc/ntpd.argv; chmod 600 /run/leon-rc/ntpd.argv");
    mark("LAB_NETWORK_SERVICES_DUPLICATE_AND_ARGUMENT_GUARDS_PASS");
    shell("for u in mdns ntpd; do ln -s /dev/null /run/systemd/system/asus-$u.service; done; systemctl daemon-reload");
    assert(start_mdns()==-1);assert(start_ntpd()==-1);
    stop_mdns();stop_ntpd();assert(launches==2 && kills==1);
    shell("rm /run/systemd/system/asus-mdns.service /run/systemd/system/asus-ntpd.service; systemctl daemon-reload; systemctl reset-failed");
    mark("LAB_NETWORK_SERVICES_FAILURE_NO_FALLBACK_PASS");
    assert(!start_mdns());assert(!start_ntpd());
    assert(!leon_rc_ready());mark("LAB_NETWORK_SERVICES_READY_PASS");
    sigemptyset(&mask);sigaddset(&mask,SIGTERM);sigaddset(&mask,SIGQUIT);
    assert(!sigwait(&mask,&sig));assert(!leon_rc_shutdown_gate(sig==SIGTERM));
    mark("LAB_NETWORK_SERVICES_DRAIN_PASS");return 0;
}
