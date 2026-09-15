#define _GNU_SOURCE
#include <stdlib.h>
#include "bootguard-crashdiag.c"

/* Normal exec preserves /proc/self/exe=/sbin/rc for ASUS identity checks.
 * Remove the loading instruction before rc can start any child services.
 * The already loaded guard remains active in this process. */
__attribute__((constructor)) static void clear_preload_environment(void)
{
    unsetenv("LD_PRELOAD");
}
