#include "rc-bridge.h"
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <sys/reboot.h>
#include <unistd.h>
int main(void)
{
    assert(leon_rc_managed());
    assert(kill(-1,0)==-1 && errno==EPERM);
    assert(kill(getpid(),0)==0);
    assert(kill(1,SIGUSR2)==0);
    assert(reboot(RB_AUTOBOOT)==0);
    puts("LAB_RC_RETAINED_OBJECT_WRAPPERS_PASS");return 0;
}
