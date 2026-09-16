#define _GNU_SOURCE
#include <execinfo.h>
#include <fcntl.h>
#include <signal.h>
#include <stdlib.h>
#include <stdio.h>
#include <ucontext.h>
#include <unistd.h>

/* Temporary, process-local diagnostic. It preserves abort's termination. */
static void trace_abort(int signal_number, siginfo_t *info, void *context)
{
    void *frames[64];
    char buffer[4096];
    int count = backtrace(frames, 64);
    int fd = open("/tmp/leon-httpd-abort.log", O_WRONLY | O_CREAT | O_APPEND, 0600);
    if (fd >= 0) {
        const char marker[] = "\nHTTPD_ABORT_BACKTRACE\n";
        (void)write(fd, marker, sizeof(marker) - 1);
        backtrace_symbols_fd(frames, count, fd);
        ucontext_t *uc = context;
        unsigned long sp = uc->uc_mcontext.arm_sp;
        dprintf(fd, "ABORT_SP=%08lx LR=%08lx PC=%08lx\n", sp,
                uc->uc_mcontext.arm_lr, uc->uc_mcontext.arm_pc);
        int mem = open("/proc/self/mem", O_RDONLY);
        int dump = open("/tmp/leon-httpd-abort-stack.bin", O_WRONLY | O_CREAT | O_TRUNC, 0600);
        if (mem >= 0 && dump >= 0) {
            char raw[8192];
            ssize_t n = pread64(mem, raw, sizeof(raw), (off64_t)sp);
            if (n > 0) (void)write(dump, raw, (size_t)n);
        }
        if (mem >= 0) close(mem);
        if (dump >= 0) close(dump);
        int maps = open("/proc/self/maps", O_RDONLY);
        if (maps >= 0) {
            ssize_t n;
            while ((n = read(maps, buffer, sizeof(buffer))) > 0) (void)write(fd, buffer, (size_t)n);
            close(maps);
        }
        close(fd);
    }
    signal(signal_number, SIG_DFL);
}

__attribute__((constructor)) static void prepare_trace(void)
{
    unsetenv("LD_PRELOAD");
    void *warmup[4];
    (void)backtrace(warmup, 4);
    struct sigaction action = {0};
    action.sa_sigaction = trace_abort;
    action.sa_flags = SA_SIGINFO;
    sigemptyset(&action.sa_mask);
    (void)sigaction(SIGABRT, &action, 0);
}
