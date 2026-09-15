#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <sys/prctl.h>
#include <unistd.h>
__attribute__((constructor)) static void preserve_init_name(void)
{
    if (getpid()==1) prctl(PR_SET_NAME,"init",0,0,0);
}
static int deny(const char *operation)
{
    dprintf(2,"LEON_TRIAL: blocked automatic boot metadata write: %s\n",operation);
    errno=EPERM;
    return -1;
}
int setBootImageState(int state) { (void)state; return deny("setBootImageState"); }
int commit(int partition,char *flag)
{
    /* The vendor API uses an initially NUL byte for a read. ASCII 0/1 writes. */
    if (flag && *flag=='\0') {
        int (*next)(int,char*)=dlsym(RTLD_NEXT,"commit");
        if (next) return next(partition,flag);
    }
    return deny("commit");
}
int setImgValidStatus(int partition,int *status)
{ (void)partition;(void)status;return deny("setImgValidStatus"); }
int setImgSeqNum(int partition,int seq)
{ (void)partition;(void)seq;return deny("setImgSeqNum"); }
int setNandMetadata(char *data,int size,int index)
{ (void)data;(void)size;(void)index;return deny("setNandMetadata"); }
int setEmmcMetadata(char *data,int size,int index)
{ (void)data;(void)size;(void)index;return deny("setEmmcMetadata"); }
