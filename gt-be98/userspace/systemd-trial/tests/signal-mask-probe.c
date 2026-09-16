#define _GNU_SOURCE
#include <assert.h>
#include <signal.h>
int main(void)
{
    sigset_t current;
    assert(!sigprocmask(SIG_SETMASK, NULL, &current));
    assert(!sigismember(&current, SIGHUP));
    assert(!sigismember(&current, SIGTERM));
    assert(!sigismember(&current, SIGUSR1));
    assert(!sigismember(&current, SIGCHLD));
    assert(!sigismember(&current, SIGALRM));
    return 0;
}
