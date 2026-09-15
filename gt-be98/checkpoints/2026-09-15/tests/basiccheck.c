#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static void check(int ok, const char *s)
{
    if (!ok) { fprintf(stderr,"LAB_FAIL %s errno=%d\n",s,errno); exit(1); }
}
static void put(const char *file,const char *value)
{
    int fd=open(file,O_WRONLY); check(fd>=0,file);
    check(write(fd,value,strlen(value))==(ssize_t)strlen(value),file); close(fd);
}
static void join(void) { put("/cg1/test/cgroup.procs","0"); }
static void waitok(pid_t p)
{
    int status; check(p>0,"fork"); check(waitpid(p,&status,0)==p,"waitpid");
    check(WIFEXITED(status)&&WEXITSTATUS(status)==0,"child status");
}
static void seccomp_test(void)
{
    pid_t p=fork();
    if (!p) {
        struct sock_filter f[]={
            BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,arch)),
            BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,0xc00000b7,1,0),
            BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL),
            BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,nr)),
            BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_getppid,0,1),
            BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|EACCES),
            BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW)};
        struct sock_fprog prog={sizeof(f)/sizeof(f[0]),f};
        check(prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0)==0,"nnp");
        check(prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&prog)==0,"seccomp");
        errno=0; check(syscall(SYS_getppid)==-1&&errno==EACCES,"filter errno");
        pid_t child=fork();
        if (!child) { errno=0; _exit(syscall(SYS_getppid)==-1&&errno==EACCES?0:2); }
        waitok(child); _exit(0);
    }
    waitok(p); puts("LAB_PASS seccomp_errno_and_fork_inheritance");
}
int main(void)
{
    check(getppid()==1&&access("/QEMU_LAB_GUEST",F_OK)==0,"QEMU guest only");
    seccomp_test();
    check(mkdir("/cg1",0755)==0,"mkdir cg1");
    check(mount("none","/cg1","cgroup",0,"cpuacct,devices,freezer")==0,"v1 mount");
    check(mkdir("/cg1/test",0755)==0,"mkdir group");
    put("/cg1/test/devices.deny","a");
    pid_t p=fork();
    if (!p) { join(); errno=0; int fd=open("/dev/null",O_WRONLY); _exit(fd<0&&errno==EPERM?0:2); }
    waitok(p); put("/cg1/test/devices.allow","c 1:3 rwm");
    p=fork();
    if (!p) { join(); int fd=open("/dev/null",O_WRONLY); _exit(fd>=0?0:2); }
    waitok(p); puts("LAB_PASS devices_deny_and_allow");
    volatile unsigned long *counter=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_ANONYMOUS,-1,0);
    check(counter!=MAP_FAILED,"mmap");
    p=fork();
    if (!p) { join(); for (;;) __atomic_fetch_add(counter,1,__ATOMIC_RELAXED); }
    check(p>0,"fork worker");
    for (int i=0;i<1000&&!*counter;i++) usleep(1000);
    check(*counter>0,"worker running");
    put("/cg1/test/freezer.state","FROZEN");
    int frozen=0;
    for (int i=0;i<1000;i++) {
        char buf[32]={0}; int fd=open("/cg1/test/freezer.state",O_RDONLY);
        check(fd>=0,"freezer state"); read(fd,buf,31); close(fd);
        if (!strncmp(buf,"FROZEN",6)) { frozen=1; break; } usleep(1000);
    }
    check(frozen,"freeze completed");
    unsigned long before=*counter; usleep(50000); check(*counter==before,"frozen worker stopped");
    put("/cg1/test/freezer.state","THAWED");
    for (int i=0;i<1000&&*counter==before;i++) usleep(1000);
    check(*counter>before,"worker resumed"); usleep(50000);
    kill(p,SIGTERM); int status; check(waitpid(p,&status,0)==p,"worker wait");
    check(WIFSIGNALED(status)&&WTERMSIG(status)==SIGTERM,"worker terminated");
    puts("LAB_PASS freezer_stop_and_resume");
    FILE *f=fopen("/cg1/test/cpuacct.usage","r"); unsigned long long usage=0;
    check(f!=NULL,"cpuacct open"); check(fscanf(f,"%llu",&usage)==1,"cpuacct read"); fclose(f);
    check(usage>0,"cpuacct accounted CPU time"); printf("LAB_PASS cpuacct_usage ns=%llu\n",usage);
    check(rmdir("/cg1/test")==0,"rmdir group"); check(umount("/cg1")==0,"umount cg1");
    check(rmdir("/cg1")==0,"rmdir cg1"); return 0;
}
