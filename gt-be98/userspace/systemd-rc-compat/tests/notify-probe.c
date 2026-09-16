#define _GNU_SOURCE
#include "rc-bridge.h"
#include <assert.h>
#include <dlfcn.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>
int nvram_set(const char *,const char *);
int notify_rc(const char *);
int notify_rc_after_wait(const char *);
int notify_rc_and_wait(const char *);
int notify_rc_and_wait_1min(const char *);
int notify_rc_and_wait_2min(const char *);
int notify_rc_after_period_wait(const char *,int);
int notify_rc_and_period_wait(const char *,int);
static volatile sig_atomic_t caught;
static void capture(int sig) { caught=sig; }
static void wait_empty(void)
{
    int i;
    for(i=0;i<100;i++) {
        if(access("/run/asus-test-nvram/rc_service",F_OK))return;
        usleep(20000);
    }
    assert(!"ASUS notification was not drained");
}
int main(int argc,char **argv)
{
    int (*simple[])(const char *)={notify_rc,notify_rc_after_wait,notify_rc_and_wait,notify_rc_and_wait_1min,notify_rc_and_wait_2min};
    unsigned i;int status, result;pid_t p;
    assert(getpid()==syscall(SYS_getpid));
    if(argc==2 && !strcmp(argv[1],"--missing")) {
        assert(notify_rc("restart_httpd")==-1);
        assert(access("/run/asus-test-nvram/rc_service",F_OK));
        puts("LAB_RC_ABSENT_BROKER_FAIL_CLOSED_PASS");return 0;
    }
    assert(!leon_rc_exchange(LEON_PING,0,NULL));
    assert(leon_rc_exchange(LEON_HELLO,0,NULL)==-1 && errno==EPERM);
    assert(leon_rc_exchange(LEON_READY,0,NULL)==-1 && errno==EPERM);
    assert(leon_rc_exchange(999,0,NULL)==-1 && errno==EINVAL);
    assert(leon_rc_exchange(LEON_SIGNAL,SIGKILL,NULL)==-1 && errno==EINVAL);
    for(i=0;i<sizeof(simple)/sizeof(simple[0]);i++) {
        result=simple[i]("restart_httpd");
        if(result)fprintf(stderr,"notify API %u returned %d, errno %d\n",i,result,errno);
        assert(!result);wait_empty();
    }
    assert(!notify_rc_after_period_wait("restart_httpd",3));wait_empty();
    assert(!notify_rc_and_period_wait("restart_httpd",3));wait_empty();
    signal(SIGUSR2,capture);
    assert(!kill(getpid(),SIGUSR2));assert(caught==SIGUSR2);
    assert(kill(999999,SIGUSR1)==-1 && errno==ESRCH);
    p=fork();assert(p>=0);
    if(!p) {
        assert(!setgid(65534));assert(!setuid(65534));
        _exit(leon_rc_exchange(LEON_SIGNAL,SIGUSR1,NULL)==-1 ? 0:1);
    }
    assert(waitpid(p,&status,0)==p && WIFEXITED(status) && !WEXITSTATUS(status));
    puts("LAB_RC_ORIGINAL_LIBSHARED_SEVEN_APIS_PASS");
    puts("LAB_RC_AUTHORIZATION_AND_SIGNAL_SCOPE_PASS");
    return 0;
}
