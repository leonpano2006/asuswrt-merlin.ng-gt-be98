#define _GNU_SOURCE
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <ucontext.h>
#include "bootguard.c"

/* Diagnostic-only extension; metadata policy is unchanged from trial 34. */
static int crashfd=-1;
static char altstack[65536];
static void hexfield(const char *key, unsigned long v)
{
    char b[128]; unsigned n=0;
    while (*key && n<80) b[n++]=*key++;
    b[n++]='='; b[n++]='0'; b[n++]='x';
    for (int shift=28;shift>=0;shift-=4) b[n++]="0123456789abcdef"[(v>>shift)&15];
    b[n++]='\n';
    if(crashfd>=0) (void)write(crashfd,b,n);
    (void)write(2,b,n);
}
static void crash(int sig,siginfo_t *info,void *opaque)
{
    if(getpid()!=1) return;
    ucontext_t *u=opaque;
    hexfield("SIG",sig); hexfield("SI_CODE",info->si_code);
    hexfield("FAULT",(uintptr_t)info->si_addr);
    hexfield("PC",u->uc_mcontext.arm_pc); hexfield("LR",u->uc_mcontext.arm_lr);
    hexfield("SP",u->uc_mcontext.arm_sp); hexfield("FP",u->uc_mcontext.arm_fp);
    hexfield("R0",u->uc_mcontext.arm_r0); hexfield("R1",u->uc_mcontext.arm_r1);
    hexfield("R2",u->uc_mcontext.arm_r2); hexfield("R3",u->uc_mcontext.arm_r3);
    hexfield("R4",u->uc_mcontext.arm_r4); hexfield("R5",u->uc_mcontext.arm_r5);
    hexfield("R6",u->uc_mcontext.arm_r6); hexfield("R7",u->uc_mcontext.arm_r7);
    hexfield("R8",u->uc_mcontext.arm_r8); hexfield("R9",u->uc_mcontext.arm_r9);
    hexfield("R10",u->uc_mcontext.arm_r10); hexfield("IP",u->uc_mcontext.arm_ip);
    /* SA_RESETHAND restores the default; the faulting instruction retries. */
}
__attribute__((constructor)) static void install_crash_diag(void)
{
    if(getpid()!=1) return;
    crashfd=open("/data/leon-trial-diag/crash.log",O_WRONLY|O_APPEND|O_CREAT|O_DSYNC|O_CLOEXEC,0600);
    if(crashfd>=0) {
        static const char start[]="BEGIN guarded init crash diagnostics\n";
        (void)write(crashfd,start,sizeof(start)-1);
        int f=open("/proc/self/maps",O_RDONLY|O_CLOEXEC); char b[4096];ssize_t n;
        if(f>=0) {while((n=read(f,b,sizeof(b)))>0)(void)write(crashfd,b,n);close(f);}
    }
    stack_t ss={.ss_sp=altstack,.ss_size=sizeof(altstack)};
    sigaltstack(&ss,0);
    struct sigaction sa={.sa_sigaction=crash,.sa_flags=SA_SIGINFO|SA_ONSTACK|SA_RESETHAND};
    sigemptyset(&sa.sa_mask);sigaction(SIGSEGV,&sa,0);
}
