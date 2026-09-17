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
#include <sys/wait.h>
#include <unistd.h>
#include "leon-daemons.h"
static int legacy;
int __real_leon_rc_managed(void);
int __wrap_leon_rc_managed(void){return legacy?0:__real_leon_rc_managed();}
int notify_rc(const char *event){(void)event;abort();}
static void shell(const char *s){char *c;assert(asprintf(&c,"set -eu; %s",s)>0);assert(!leon_rc_system(c));free(c);}
static void mark(const char *s){puts(s);fflush(stdout);}
static void reap(int s){int e=errno;(void)s;while(waitpid(-1,NULL,WNOHANG)>0){}errno=e;}
int main(int argc,char **argv)
{
 int status,sig,i=0;pid_t child;sigset_t mask;struct sigaction sa={.sa_handler=reap};
 const struct leon_daemon *d;
 assert(!leon_rc_manager_enter(argc,argv));
 legacy=1;assert(leon_rc_daemon_status("syslogd",1,NULL)==1);legacy=0;
 child=fork();assert(child>=0);if(!child){errno=0;_exit(!(leon_rc_daemon_status("syslogd",1,NULL)==-1 && errno==EPERM));}
 assert(waitpid(child,&status,0)==child && WIFEXITED(status) && !WEXITSTATUS(status));
 sigemptyset(&sa.sa_mask);assert(!sigaction(SIGCHLD,&sa,NULL));
 assert(leon_rc_daemon_status("unknown",1,NULL)==-1);
 mark("LAB_PLATFORM_MANAGER_AUTH_PASS");
 for(d=leon_daemons;d->name;d++,i++){
  char *a[]={(char *)d->comm,(char *)d->name,!strcmp(d->name,"eapd")?"3":(i%2?"2":"0"),NULL};
  assert(!leon_rc_daemon_status(d->name,1,a));
 }
 shell("test $(systemctl show asus-rc.service -p ActiveState --value) = activating; /usr/libexec/check-platform-fixtures");
 mark("LAB_PLATFORM_23_PRE_READY_START_PASS");
 shell("sleep 300 & echo $! >/run/platform-outsider; for u in eapd httpds6 notification smbd; do p=$(systemctl show asus-$u.service -p MainPID --value); systemctl kill --kill-whom=main --signal=KILL asus-$u.service; i=0; while :; do n=$(systemctl show asus-$u.service -p MainPID --value); if test $n -gt 1 && test $n != $p && systemctl is-active --quiet asus-$u.service; then break; fi; i=$((i+1)); test $i -lt 12; sleep 1; done; done; /usr/libexec/check-platform-fixtures");
 mark("LAB_PLATFORM_SUPERVISOR_RECOVERY_PASS");
 shell("p=$(cat /run/fixture-notification); kill -KILL $p; i=0; while test $(cat /run/fixture-notification) = $p || ! systemctl is-active --quiet asus-notification.service; do i=$((i+1)); test $i -lt 12; sleep 1; done; /usr/libexec/check-platform-fixtures");
 mark("LAB_PLATFORM_PRIMARY_EXIT_WITH_WORKER_PASS");
 for(d=leon_daemons;d->name;d++)assert(!leon_rc_daemon_status(d->name,0,NULL));
 shell("test -d /proc/$(cat /run/platform-outsider); ! /bin/busybox pidof nt_center; for u in $(cat /usr/libexec/platform-unit-list); do test $(systemctl show asus-$u.service -p ActiveState --value) = inactive; p=$(cat /run/fixture-$u); test ! -d /proc/$p; done");
 mark("LAB_PLATFORM_STOP_GROUP_ISOLATION_PASS");
 shell("/usr/sbin/bsd external 0 & p=$!; sleep 1; if systemctl start asus-bsd.service; then exit 1; fi; systemctl stop asus-bsd.service; test -d /proc/$p; kill $p; wait $p; systemctl reset-failed");
 mark("LAB_PLATFORM_EXTERNAL_DUPLICATE_PASS");
 shell("cp /run/leon-rc/bsd.argv /run/bsd.good; chmod 666 /run/leon-rc/bsd.argv; if /usr/libexec/leon-daemon-supervisor bsd; then exit 1; fi; rm /run/leon-rc/bsd.argv; ln -s /run/bsd.good /run/leon-rc/bsd.argv; if /usr/libexec/leon-daemon-supervisor bsd; then exit 1; fi; rm /run/leon-rc/bsd.argv; mv /run/bsd.good /run/leon-rc/bsd.argv; chmod 600 /run/leon-rc/bsd.argv; ln -s /dev/null /run/systemd/system/asus-bsd.service; systemctl daemon-reload");
 char *b[]={"bsd","bsd","2",NULL};assert(leon_rc_daemon_status("bsd",1,b)==-1);
 shell("rm /run/systemd/system/asus-bsd.service; systemctl daemon-reload; systemctl reset-failed; kill $(cat /run/platform-outsider)");
 mark("LAB_PLATFORM_BAD_CONFIG_NO_FALLBACK_PASS");
 for(d=leon_daemons;d->name;d++){char *a[]={(char *)d->comm,(char *)d->name,"2",NULL};assert(!leon_rc_daemon_status(d->name,1,a));}
 assert(!leon_rc_ready());mark("LAB_PLATFORM_READY_PASS");
 sigemptyset(&mask);sigaddset(&mask,SIGTERM);sigaddset(&mask,SIGQUIT);assert(!sigwait(&mask,&sig));assert(!leon_rc_shutdown_gate(sig==SIGTERM));
 mark("LAB_PLATFORM_DRAIN_PASS");return 0;
}
