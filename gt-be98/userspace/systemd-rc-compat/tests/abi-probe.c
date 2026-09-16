#define _GNU_SOURCE
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <unistd.h>
int main(void) {
    assert(getpid()==syscall(SYS_getpid));
    assert(dlsym(RTLD_DEFAULT,"notify_rc_and_wait"));
    puts("LAB_RC_MULTIARCH_PRELOAD_PASS");return 0;
}
