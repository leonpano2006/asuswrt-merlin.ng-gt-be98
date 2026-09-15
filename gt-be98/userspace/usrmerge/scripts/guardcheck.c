#include <stdio.h>
#include <sys/reboot.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
int commit(int,char*),setBootImageState(int),setImgValidStatus(int,int*),setImgSeqNum(int,int);
int setNandMetadata(char*,int,int),setEmmcMetadata(char*,int,int);
int main(int argc,char **argv)
{
    if (argc==2 && !strcmp(argv[1],"--child"))
        return setBootImageState(0)==91?0:1;
    if (strcmp(argv[0],"/sbin/init") || getenv("LD_PRELOAD")) return 2;
    char flag=0;
    if (commit(1,&flag)!=0||flag!='1') return 3;
    flag='1';if(commit(2,&flag)!=-1) return 4;
    flag='0';if(commit(1,&flag)!=-1) return 5;
    int status=1;
    if(setBootImageState(0)!=-1||setImgValidStatus(1,&status)!=-1||setImgSeqNum(1,99)!=-1
       ||setNandMetadata(NULL,0,0)!=-1||setEmmcMetadata(NULL,0,0)!=-1) return 6;
    pid_t p=fork();
    if(!p) { execl("/sbin/rc","/sbin/rc","--child",NULL);_exit(7); }
    if(p<0||waitpid(p,&status,0)!=p||!WIFEXITED(status)||WEXITSTATUS(status))return 8;
    puts("LAB_PASS trial_init_argv0_metadata_write_guard_and_no_exec_inheritance");
    puts("QEMU_USRMERGE_COMPLETE");
    fflush(stdout);
    sync();
    reboot(RB_POWER_OFF);
    for (;;) pause();
}
