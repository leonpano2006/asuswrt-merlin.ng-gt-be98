/* Real ssh.o, manager bridge and foreground Dropbear; only NVRAM is stubbed. */
#define _GNU_SOURCE
#include "rc-bridge.h"
#include "rc-services.h"
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

int start_sshd(void);
void stop_sshd(void);
int __real_leon_rc_managed(void);
static int legacy, launches, kills, notified, enabled=1, pass, forwarding;
static char port[16]="2222", public_key[2048], window[16]="65536";
int __wrap_leon_rc_managed(void) { return legacy ? 0 : __real_leon_rc_managed(); }
char *nvram_get(const char *name)
{
    if (!strcmp(name,"sshd_port")) return port;
    if (!strcmp(name,"sshd_authkeys")) return public_key;
    if (!strcmp(name,"sshd_rwb")) return window;
    return "";
}
int nvram_get_int(const char *name)
{
    if (!strcmp(name,"sshd_enable")) return enabled;
    if (!strcmp(name,"sshd_pass")) return pass;
    if (!strcmp(name,"sshd_forwarding")) return forwarding;
    return atoi(nvram_get(name));
}
int nvram_set_int(const char *name,int value) { assert(!strcmp(name,"sshd_enable"));enabled=value;return 0; }
int nvram_set(const char *name,const char *value) { assert(!strcmp(name,"sshd_port"));snprintf(port,sizeof(port),"%s",value);return 0; }
char *nvram_default_get(const char *name) { assert(!strcmp(name,"sshd_port"));return "22"; }
int notify_rc(const char *event)
{
    assert(!leon_rc_is_manager());
    if (!strcmp(event,"start_sshd")) notified|=1;
    else if (!strcmp(event,"stop_sshd")) notified|=2;
    else abort();
    return 0;
}
int _eval(char *const argv[],const char *path,int timeout,pid_t *pid)
{
    int status;pid_t child;
    assert(!path && !timeout && !pid);
    if (!strcmp(argv[0],"dropbear")) {
        assert(legacy);
        for (int i=1;argv[i];i++) assert(strcmp(argv[i],"-F"));
        launches++;return 0;
    }
    assert(!strcmp(argv[0],"dropbearkey") || !strcmp(argv[0],"ln"));
    child=fork();assert(child>=0);
    if (!child) { sigset_t mask;sigemptyset(&mask);sigprocmask(SIG_SETMASK,&mask,NULL);execvp(argv[0],argv);_exit(127); }
    assert(waitpid(child,&status,0)==child && WIFEXITED(status));
    return WEXITSTATUS(status); /* ln may report an existing host-key link. */
}
int d_exists(const char *path) { struct stat s;return !stat(path,&s) && S_ISDIR(s.st_mode); }
int f_exists(const char *path) { return access(path,F_OK)==0; }
void replace_char(char *s,char old,char new) { for (;*s;s++) if (*s==old) *s=new; }
int f_write_string(const char *path,const char *s,unsigned flags,unsigned mode)
{
    assert(!flags);FILE *f=fopen(path,"w");assert(f);assert(fputs(s,f)>=0);assert(!fclose(f));assert(!chmod(path,mode));return strlen(s);
}
int pids(const char *name) { assert(!strcmp(name,"dropbear"));return legacy; }
void killall_tk(const char *name) { assert(legacy && !strcmp(name,"dropbear"));kills++; }
void logmessage_normal(const char *name,const char *fmt,...) { (void)name;(void)fmt; }
static void shell(const char *s)
{
    char *cmd;assert(asprintf(&cmd,"set -eu; %s",s)>0);assert(!leon_rc_system(cmd));free(cmd);
}
static void mark(const char *s) { puts(s);fflush(stdout); }
int main(int argc,char **argv)
{
    int status,sig;pid_t child;sigset_t mask;FILE *f;
    assert(!leon_rc_manager_enter(argc,argv));umask(0);
    f=fopen("/run/ssh-test.pub","r");assert(f && fgets(public_key,sizeof(public_key),f));fclose(f);
    enabled=0;assert(!start_sshd());assert(launches==0);enabled=1;
    strcpy(port,"70000");assert(!start_sshd());assert(!enabled && !strcmp(port,"22"));enabled=1;strcpy(port,"2222");
    legacy=1;assert(!start_sshd());stop_sshd();assert(launches==1 && kills==1);legacy=0;
    child=fork();assert(child>=0);
    if (!child) {
        assert(leon_rc_sshd(1,NULL)==-1 && errno==EPERM);
        assert(!start_sshd());stop_sshd();_exit(notified!=3);
    }
    assert(waitpid(child,&status,0)==child && WIFEXITED(status) && !WEXITSTATUS(status));
    mark("LAB_SSH_LEGACY_POLICY_CHILD_ROUTING_PASS");
    assert(!start_sshd());
    shell("test $(systemctl show asus-rc.service -p ActiveState --value) = activating; /usr/libexec/check-ssh-daemon 2222 strict; "
          "sha256sum /jffs/.ssh/* > /run/ssh-hostkeys-first; "
          "systemctl show asus-sshd.service -p MainPID --value > /run/sshd-first");
    assert(!start_sshd());
    shell("test $(cat /run/sshd-first) = $(systemctl show asus-sshd.service -p MainPID --value); "
          "sha256sum -c /run/ssh-hostkeys-first; /usr/libexec/check-ssh-daemon 2222 strict session");
    mark("LAB_SSH_PRE_READY_AUTH_KEYS_IDEMPOTENT_PASS");
    stop_sshd();
    shell("/usr/libexec/check-ssh-stopped; sleep 300 & echo $! > /run/rc-independent-child");
    strcpy(port,"2223");pass=1;forwarding=1;strcpy(window,"0");
    assert(!start_sshd());
    shell("/usr/libexec/check-ssh-daemon 2223 permissive; sha256sum -c /run/ssh-hostkeys-first; "
          "p=$(systemctl show asus-sshd.service -p MainPID --value); "
          "systemctl kill --kill-whom=main --signal=KILL asus-sshd.service; i=0; "
          "while :; do n=$(systemctl show asus-sshd.service -p MainPID --value); "
          "if test $n -gt 1 && test $n != $p; then break; fi; i=$((i+1)); test $i -lt 12; sleep 1; done; "
          "/usr/libexec/check-ssh-daemon 2223 permissive; test -d /proc/$(cat /run/rc-independent-child)");
    stop_sshd();
    shell("test $(systemctl show asus-sshd.service -p ActiveState --value) = inactive; "
          "! /bin/busybox pidof dropbear; test -d /proc/$(cat /run/rc-independent-child); kill $(cat /run/rc-independent-child)");
    mark("LAB_SSH_RECONFIGURE_RECOVERY_ISOLATION_PASS");
    shell("/usr/libexec/leon-service-exec sshd & outsider=$!; i=0; "
          "until test \"$(/bin/busybox pidof dropbear)\" = $outsider; do i=$((i+1)); test $i -lt 10; sleep 1; done; "
          "if systemctl start asus-sshd.service; then exit 1; fi; systemctl stop asus-sshd.service; "
          "test -d /proc/$outsider; kill $outsider; wait $outsider || :; systemctl reset-failed");
    assert(leon_rc_sshd(1,NULL)==-1 && errno==EINVAL);
    shell("cp /run/leon-rc/sshd.argv /run/sshd-args-saved; chmod 666 /run/leon-rc/sshd.argv; "
          "if /usr/libexec/leon-service-exec sshd; then exit 1; fi; "
          "chmod 600 /run/leon-rc/sshd.argv; printf bad > /run/leon-rc/sshd.argv; "
          "if /usr/libexec/leon-service-exec sshd; then exit 1; fi; "
          "rm /run/leon-rc/sshd.argv; ln -s /run/sshd-args-saved /run/leon-rc/sshd.argv; "
          "if /usr/libexec/leon-service-exec sshd; then exit 1; fi; "
          "rm /run/leon-rc/sshd.argv; mv /run/sshd-args-saved /run/leon-rc/sshd.argv; chmod 600 /run/leon-rc/sshd.argv");
    mark("LAB_SSH_DUPLICATE_ARGUMENT_GUARDS_PASS");
    shell("ln -s /dev/null /run/systemd/system/asus-sshd.service; systemctl daemon-reload");
    assert(start_sshd()==-1);stop_sshd();assert(launches==1 && kills==1);
    shell("rm /run/systemd/system/asus-sshd.service; systemctl daemon-reload; systemctl reset-failed");
    mark("LAB_SSH_FAILURE_NO_FALLBACK_PASS");
    assert(!start_sshd());shell("/usr/libexec/check-ssh-daemon 2223 permissive session");
    assert(!leon_rc_ready());mark("LAB_SSH_READY_PASS");
    sigemptyset(&mask);sigaddset(&mask,SIGTERM);sigaddset(&mask,SIGQUIT);
    assert(!sigwait(&mask,&sig));assert(!leon_rc_shutdown_gate(sig==SIGTERM));
    mark("LAB_SSH_DRAIN_PASS");return 0;
}
