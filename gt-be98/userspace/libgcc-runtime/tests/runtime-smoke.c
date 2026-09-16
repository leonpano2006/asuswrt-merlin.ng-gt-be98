#define _GNU_SOURCE
#include <assert.h>
#include <dlfcn.h>
#include <pthread.h>
#include <semaphore.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unwind.h>
#include <unistd.h>

static sem_t ready;
static int cleaned;
static void cleanup(void *arg) { (*(int *)arg)++; }
static void *worker(void *unused)
{
    (void)unused;
    pthread_cleanup_push(cleanup, &cleaned);
    assert(sem_post(&ready) == 0);
    for (;;) pause();
    pthread_cleanup_pop(0);
    return NULL;
}
static _Unwind_Reason_Code frame(struct _Unwind_Context *ctx, void *arg)
{
    if (_Unwind_GetIP(ctx)) (*(unsigned *)arg)++;
    return _URC_NO_REASON;
}
__attribute__((noinline)) static unsigned trace(void)
{
    unsigned frames = 0;
    _Unwind_Backtrace(frame, &frames);
    return frames;
}
int main(void)
{
    void *lib = dlopen("libgcc_s.so.1", RTLD_NOW | RTLD_LOCAL);
    assert(lib != NULL);
    void *symbol = dlsym(lib, "_Unwind_Backtrace");
    Dl_info info;
    assert(symbol != NULL && dladdr(symbol, &info) != 0);
    const char *triplet = getenv("EXPECTED_TRIPLET");
    assert(triplet != NULL && strstr(info.dli_fname, triplet) != NULL);
    printf("LIBGCC_PROVIDER %s\n", info.dli_fname);
    unsigned frames = trace();
    assert(frames >= 3);
    printf("PASS unwind_backtrace frames=%u\n", frames);
#if defined(__aarch64__)
    typedef __int128 wide;
    wide (*divide)(wide, wide) = (wide (*)(wide, wide))dlsym(lib, "__divti3");
    wide quotient = ((wide)1 << 90) + 12345;
#else
    typedef long long wide;
    wide (*divide)(wide, wide) = (wide (*)(wide, wide))dlsym(lib, "__divdi3");
    wide quotient = 1234567890123LL;
#endif
    assert(divide != NULL);
    assert(divide(quotient * 97 + 17, 97) == quotient);
    assert(divide(-(quotient * 97 + 17), 97) == -quotient);
    puts("PASS libgcc_signed_wide_division");
    assert(sem_init(&ready, 0, 0) == 0);
    pthread_t thread;
    assert(pthread_create(&thread, NULL, worker, NULL) == 0);
    assert(sem_wait(&ready) == 0);
    assert(pthread_cancel(thread) == 0);
    void *result = NULL;
    assert(pthread_join(thread, &result) == 0);
    assert(result == PTHREAD_CANCELED && cleaned == 1);
    assert(sem_destroy(&ready) == 0);
    puts("PASS pthread_cancel_forced_unwind_cleanup");
    assert(dlclose(lib) == 0);
    puts("LIBGCC_RUNTIME_SMOKE_PASS");
    return 0;
}
