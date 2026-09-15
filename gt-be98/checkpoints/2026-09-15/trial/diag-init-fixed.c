#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <time.h>
#include <unistd.h>
extern char **environ;
static int logfd=-1;
static void record(const char *fmt,...)
{
    char b[1024];struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);
    int n=snprintf(b,sizeof(b),"%ld.%03ld ",(long)t.tv_sec,t.tv_nsec/1000000);
    va_list a;va_start(a,fmt);vsnprintf(b+n,sizeof(b)-n,fmt,a);va_end(a);
    if(logfd>=0)dprintf(logfd,"%s\n",b);
    dprintf(2,"LEON_DIAG %s\n",b);
}
static int readtext(const char*p,char*b,size_t n)
{int f=open(p,O_RDONLY|O_CLOEXEC);if(f<0)return-1;int z=read(f,b,n-1);close(f);if(z<0)return-1;b[z]=0;return z;}
static int seen(const char *item,char list[][128],int *count)
{for(int i=0;i<*count;i++)if(!strcmp(list[i],item))return 1;if(*count<256)snprintf(list[(*count)++],128,"%s",item);return 0;}
static void watch(void)
{
    prctl(PR_SET_NAME,"leon-bootlog",0,0,0);
    int k=open("/dev/kmsg",O_RDONLY|O_NONBLOCK|O_CLOEXEC);char modules[256][128],loading[256][128],b[16384];int nm=0,nl=0,context=0;
    char oldw[256]="",w[256],p[128],comm[128];
    for(int tick=0;tick<1500;tick++) {
        if(k>=0) for(int i=0;i<200;i++) {
            int z=read(k,b,sizeof(b)-1);if(z<0)break;b[z]=0;
            int start=strstr(b,"Kernel panic")||strstr(b,"Internal error")||strstr(b,"Call trace:")||strstr(b,"BUG:");
            if(start)context=36;
            if(context||strstr(b,"initcall ")||strstr(b,"calling ")) {record("KERNEL %s",b);if(context)context--;}
        }
        FILE*f=fopen("/proc/modules","r");if(f){while(fgets(b,sizeof(b),f)){char name[128];if(sscanf(b,"%127s",name)==1&&!seen(name,modules,&nm))record("MODULE_LOADED %s",name);}fclose(f);}
        DIR*d=opendir("/proc");struct dirent*de;
        if(d){while((de=readdir(d))) {
            if(de->d_name[0]<'0'||de->d_name[0]>'9'||strlen(de->d_name)>10)continue;
            snprintf(p,sizeof(p),"/proc/%s/comm",de->d_name);if(readtext(p,comm,sizeof(comm))<0)continue;
            if(strcmp(comm,"insmod\n")&&strcmp(comm,"modprobe\n"))continue;
            snprintf(p,sizeof(p),"/proc/%s/cmdline",de->d_name);int z=readtext(p,b,sizeof(b));if(z<0)continue;
            for(int j=0;j<z;){char*arg=b+j;size_t len=strnlen(arg,z-j);if(len&&len<128&&strstr(arg,".ko")&&!seen(arg,loading,&nl))record("MODULE_LOADING %s",arg);j+=len+1;}
        }closedir(d);}
        if(tick%5==0&&readtext("/proc/1/wchan",w,sizeof(w))>=0&&strcmp(w,oldw)){record("PID1_WAIT %s",w);snprintf(oldw,sizeof(oldw),"%s",w);}
        usleep(200000);
    }
    record("LOGGER_DONE");_exit(0);
}
int main(int argc,char **argv)
{
    if(getpid()!=1){fprintf(stderr,"diagnostic init is PID 1 only\n");return 1;}
    prctl(PR_SET_NAME,"init",0,0,0);
    mount("proc","/proc","proc",0,NULL);
    mount("sysfs","/sys","sysfs",0,NULL);
    int mounted=mount("ubi:data","/data","ubifs",0,NULL),err=errno;
    if(mounted==0||err==EBUSY){mkdir("/data/leon-trial-diag",0700);logfd=open("/data/leon-trial-diag/boot.log",O_WRONLY|O_CREAT|O_APPEND|O_DSYNC|O_CLOEXEC,0600);}
    struct utsname u;uname(&u);record("BEGIN version=%s data_mount=%d errno=%d",u.version,mounted,err);
    char cmdline[2048];if(readtext("/proc/cmdline",cmdline,sizeof(cmdline))>=0)record("ROOT_SLOT %s",strstr(cmdline,"ubiblock0_6")?"2":strstr(cmdline,"ubiblock0_4")?"1":"other");
    /* Kernel PID 1 normally receives the kernel's default PATH. Preserve it. */
    if(!getenv("PATH"))setenv("PATH","/sbin:/usr/sbin:/bin:/usr/bin",1);
    pid_t child=fork();if(child==0)watch();record("LOGGER_PID %d",child);
    char **args=calloc((size_t)argc+1,sizeof(*args));
    if(args && setenv("LD_PRELOAD","/usr/lib/leon-trial-bootguard.so",1)==0){
        args[0]="/sbin/init";
        for(int i=1;i<argc;i++)args[i]=argv[i];
        record("EXEC_NORMAL_GUARDED_RC");execve("/sbin/rc",args,environ);
    }
    record("EXEC_FAILED errno=%d",errno);for(;;)pause();
}
