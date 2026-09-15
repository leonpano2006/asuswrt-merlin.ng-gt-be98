#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
int main(void)
{
    char exe[256];ssize_t n=readlink("/proc/self/exe",exe,sizeof(exe)-1);
    if(n<0)return 3;
    exe[n]=0;
    void *h=dlopen("libshared.so",RTLD_LAZY|RTLD_GLOBAL);
    if(!h){fprintf(stderr,"dlopen failed: %s\n",dlerror());return 4;}
    int (*check)(void)=dlsym(h,"invalid_program_check");
    if(!check)return 5;
    int result=check();
    printf("LAB_IDENTITY exe=%s result=%d preload_env=%s\n",exe,result,getenv("LD_PRELOAD")?"present":"absent");
    return result;
}
