#define _GNU_SOURCE
#include <assert.h>
#include <gnu/libc-version.h>
#include <math.h>
#include <netdb.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
static __thread int tls;
static void *worker(void *arg)
{
    tls = 73;
    char *p = malloc(65536);
    assert(p);
    memset(p, 0x55, 65536);
    memmove(p + 1, p, 65535);
    assert(p[65535] == 0x55 && tls == 73);
    free(p);
    return arg;
}
int main(void)
{
    pthread_t t;
    void *ret;
    int token = 1;
    assert(!pthread_create(&t, NULL, worker, &token));
    assert(!pthread_join(t, &ret) && ret == &token && tls == 0);
    volatile double x = 0.5;
    assert(fabs(sin(x) - 0.479425538604203) < 1e-12);
    struct addrinfo hints = {.ai_family = AF_INET, .ai_flags = AI_NUMERICHOST}, *answer;
    assert(!getaddrinfo("127.0.0.1", NULL, &hints, &answer));
    freeaddrinfo(answer);
    assert(!strcmp(gnu_get_libc_version(), "2.44"));
    printf("LAB_ABI_PASS bits=%zu glibc=%s hwcap=%lx\n",
           sizeof(void *) * 8, gnu_get_libc_version(), getauxval(AT_HWCAP));
    return 0;
}
