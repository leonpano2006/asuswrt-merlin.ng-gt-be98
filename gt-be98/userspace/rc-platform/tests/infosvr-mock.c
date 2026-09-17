/* Offline lifecycle substitute. It does not test Broadcom NVRAM or discovery. */
#define _GNU_SOURCE
#include <assert.h>
#include <string.h>
#include <sys/prctl.h>
#include <unistd.h>
int main(int argc, char **argv)
{
    assert(argc == 2 && !strcmp(argv[1], "br0"));
    assert(!prctl(PR_SET_NAME, "infosvr", 0, 0, 0));
    for (;;) pause();
}
