#include <stdio.h>
#include <stdlib.h>
#include <stdatomic.h>
#include <pthread.h>
#include <complex.h>
#include <math.h>
#include <gnu/libc-version.h>

static atomic_int count;
static void *worker(void *arg) {
    (void)arg;
    for (int i = 0; i < 10000; ++i) atomic_fetch_add(&count, 1);
    return NULL;
}
int main(void) {
    pthread_t a, b;
    if (pthread_create(&a, NULL, worker, NULL) ||
        pthread_create(&b, NULL, worker, NULL)) return 1;
    if (pthread_join(a, NULL) || pthread_join(b, NULL)) return 2;
    volatile double complex x = 1.0 + 2.0 * I;
    volatile double complex y = 3.0 + 4.0 * I;
    double complex z = x * y;
    if (atomic_load(&count) != 20000 || fabs(creal(z) + 5.0) > 1e-9 ||
        fabs(cimag(z) - 10.0) > 1e-9) return 3;
    printf("C PASS gcc=%s glibc=%s count=%d\n", __VERSION__,
           gnu_get_libc_version(), atomic_load(&count));
    return 0;
}
