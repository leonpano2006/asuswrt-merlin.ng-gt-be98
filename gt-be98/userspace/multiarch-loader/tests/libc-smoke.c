#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <gnu/libc-version.h>
#include <iconv.h>
#include <math.h>
#include <netdb.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/random.h>
#include <time.h>

static __thread unsigned tls_value;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned total;
static void *worker(void *arg)
{
    unsigned id = (unsigned)(uintptr_t)arg;
    tls_value = id;
    for (unsigned i = 0; i < 2000; i++) {
        void *p = malloc(123 + i % 256);
        assert(p != NULL);
        memset(p, (int)id, 123 + i % 256);
        free(p);
        assert(pthread_mutex_lock(&lock) == 0);
        total++;
        assert(pthread_mutex_unlock(&lock) == 0);
        assert(tls_value == id);
    }
    return (void *)(uintptr_t)tls_value;
}

int main(void)
{
    printf("GLIBC_VERSION %s\n", gnu_get_libc_version());
    assert(strcmp(gnu_get_libc_version(), "2.44") == 0);
    printf("ABI_BITS %zu HWCAP 0x%lx HWCAP2 0x%lx\n",
           sizeof(void *) * 8, getauxval(AT_HWCAP), getauxval(AT_HWCAP2));
    unsigned char *a, *b, *ref;
    assert(posix_memalign((void **)&a, 64, 262272) == 0);
    assert(posix_memalign((void **)&b, 64, 262272) == 0);
    assert(posix_memalign((void **)&ref, 64, 262272) == 0);
    for (size_t i = 0; i < 262272; i++) a[i] = (unsigned char)(i * 17 + 3);
    for (size_t n = 0; n < 262144; n = n < 128 ? n + 1 : n * 2 + 1) {
        for (size_t off = 0; off < 32; off++) {
            memset(b, 0xa5, 262272);
            memcpy(b + off, a + 31 - off, n);
            assert(memcmp(b + off, a + 31 - off, n) == 0);
            assert(b[n + off] == 0xa5);
            memcpy(b, a, 262272);
            memcpy(ref, a, 262272);
            for (size_t i = n; i > 0; i--) ref[i - 1 + off] = ref[i - 1];
            memmove(b + off, b, n);
            assert(memcmp(b, ref, 262272) == 0);
        }
    }
    free(a); free(b); free(ref);
    puts("PASS memory_alignment_overlap_and_allocator");
    pthread_t threads[4];
    for (uintptr_t i = 0; i < 4; i++) assert(pthread_create(&threads[i], NULL, worker, (void *)(i + 1)) == 0);
    for (uintptr_t i = 0; i < 4; i++) {
        void *result;
        assert(pthread_join(threads[i], &result) == 0);
        assert((uintptr_t)result == i + 1);
    }
    assert(total == 8000 && tls_value == 0);
    puts("PASS pthread_tls_mutex");
    volatile double x = 0.5;
    assert(fabs(sin(x) - 0.479425538604203) < 1e-12);
    assert(fabs(sqrt(x) - 0.707106781186548) < 1e-12);
    puts("PASS floating_point_libm");
    unsigned char random_bytes[32];
    assert(getrandom(random_bytes, sizeof(random_bytes), 0) == sizeof(random_bytes));
    struct timespec now;
    assert(clock_gettime(CLOCK_MONOTONIC, &now) == 0);
    struct addrinfo hints = {.ai_family = AF_INET, .ai_flags = AI_NUMERICHOST}, *answer;
    assert(getaddrinfo("127.0.0.1", NULL, &hints, &answer) == 0);
    freeaddrinfo(answer);
    puts("PASS kernel_calls_and_numeric_resolver");
    iconv_t cd = iconv_open("UTF-16LE", "UTF-8");
    assert(cd != (iconv_t)-1);
    char input[] = "A\xe5\x8f\xb0", output[16] = {0};
    char *in = input, *out = output;
    size_t inleft = sizeof(input) - 1, outleft = sizeof(output);
    assert(iconv(cd, &in, &inleft, &out, &outleft) != (size_t)-1);
    assert(inleft == 0 && out - output == 4);
    assert(memcmp(output, "\x41\0\xf0\x53", 4) == 0);
    assert(iconv_close(cd) == 0);
    puts("PASS gconv_utf8_utf16");
    puts("GLIBC_B53_SMOKE_COMPLETE");
    return 0;
}
