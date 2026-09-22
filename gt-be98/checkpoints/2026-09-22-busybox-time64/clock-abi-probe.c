#define _GNU_SOURCE
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

int main(void)
{
    struct timespec raw, before, after;
    unsigned char *bytes = (unsigned char *)&raw;
    memset(&raw, 0xa5, sizeof(raw));
    if (clock_gettime(CLOCK_MONOTONIC, &before)) return 1;
    if (syscall(SYS_clock_gettime, CLOCK_MONOTONIC, &raw)) return 2;
    printf("time_t=%zu timespec=%zu nsec_offset=%zu raw_bytes=",
           sizeof(time_t), sizeof(raw), offsetof(struct timespec, tv_nsec));
    for (size_t i = 0; i < sizeof(raw); ++i) printf("%02x", bytes[i]);
    printf("\nraw_sec=%lld raw_nsec=%ld libc_sec=%lld libc_nsec=%ld\n",
           (long long)raw.tv_sec, raw.tv_nsec,
           (long long)before.tv_sec, before.tv_nsec);
    usleep(50000);
    if (clock_gettime(CLOCK_MONOTONIC, &after)) return 3;
    long long delta = (long long)(after.tv_sec - before.tv_sec) * 1000000000LL
                      + after.tv_nsec - before.tv_nsec;
    printf("libc_sleep_delta_ns=%lld\n", delta);
    return delta >= 40000000LL && delta < 1000000000LL ? 0 : 4;
}
