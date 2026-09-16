/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _GNU_SOURCE
#include <assert.h>
#include <dlfcn.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

static pid_t manager_pid;
static int notifications, already_running;
#ifndef NO_MANAGER_EXPORT
int leon_rc_is_manager(void) { return manager_pid > 1 && getpid() == manager_pid; }
#endif
int notify_rc(const char *event) { assert(event && *event); notifications++; return 0; }
int pidof(const char *name) { assert(name && *name); already_running++; return 42; }
void logmessage(const char *header, const char *format, ...) { (void)header; (void)format; }

int main(int argc, char **argv)
{
    static const char *names[] = { "ovpn_start_client", "ovpn_start_server", "ovpn_stop_client", "ovpn_stop_server" };
    void (*functions[4])(int);
    void *library;
    pid_t child;
    int status;
    assert(argc == 2 && getpid() > 1);
    library=dlopen(argv[1], RTLD_NOW|RTLD_LOCAL);
    if (!library) { fprintf(stderr, "%s\n", dlerror()); return 2; }
    for (int i=0;i<4;i++) {
        *(void **)(&functions[i])=dlsym(library,names[i]); assert(functions[i]);
        functions[i](1);
    }
    assert(notifications == 4 && already_running == 0);
#ifndef NO_MANAGER_EXPORT
    manager_pid=getpid();
    /* The real library takes its existing already-running exit before I/O. */
    functions[0](1); functions[1](1);
    if (notifications == 6 && already_running == 0) {
        puts("LAB_OVPN_STOCK_MANAGER_REQUEUES_REPRODUCED"); return 77;
    }
    assert(notifications == 4 && already_running == 2);
#endif
    child=fork(); assert(child >= 0);
    if (!child) {
        int before=notifications;
        for (int i=0;i<4;i++) functions[i](1);
        _exit(notifications != before+4);
    }
    assert(waitpid(child,&status,0)==child && WIFEXITED(status) && !WEXITSTATUS(status));
    dlclose(library);
#ifdef NO_MANAGER_EXPORT
    puts("LAB_OVPN_UNMODIFIED_CALLER_FALLBACK_PASS");
#else
    puts("LAB_OVPN_MANAGER_AND_FORK_ROLE_PASS");
#endif
    return 0;
}
