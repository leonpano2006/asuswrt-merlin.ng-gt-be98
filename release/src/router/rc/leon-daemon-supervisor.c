/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <sched.h>
#include <signal.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include "leon-daemons.h"

/* ASUS programs may double-fork and some have no foreground option. Adopt
 * only our own descendants, retain a stable main PID for systemd, and watch
 * the actual daemon rather than its short-lived launcher. systemd alone
 * kills/restarts the cgroup. No global killall, PID adoption or shell. */
static volatile sig_atomic_t stopping;
static void stop(int sig) { (void)sig; stopping = 1; }
static int read_comm(pid_t pid, char *out, size_t size)
{
    char path[80]; FILE *f;
    snprintf(path, sizeof(path), "/proc/%ld/comm", (long)pid);
    f = fopen(path, "re"); if (!f) return -1;
    if (!fgets(out, size, f)) { fclose(f); return -1; }
    fclose(f); out[strcspn(out, "\n")] = 0; return 0;
}
static int duplicate(const struct leon_daemon *d)
{
    DIR *dir = opendir("/proc"); struct dirent *e;
    char comm[64], path[80], line[512]; pid_t pid;
    if (!dir) return -1;
    while ((e = readdir(dir))) {
        char *end; long n = strtol(e->d_name, &end, 10);
        if (*end || n <= 1) continue;
        pid = n;
        if (read_comm(pid, comm, sizeof(comm))) continue;
        if (strcmp(comm, d->comm) &&
            (strcmp(d->name, "notification") || strcmp(comm, "nt_center"))) continue;
        /* LAN/WAN HTTPS are separate legitimate instances. Only existing
         * systemd-owned sibling units may share the httpds process name. */
        if (!strcmp(comm, "httpds")) {
            int sibling = 0; FILE *f;
            snprintf(path, sizeof(path), "/proc/%ld/cgroup", (long)pid);
            f = fopen(path, "re");
            if (f) {
                while (fgets(line, sizeof(line), f)) {
                    const char *own = !strcmp(d->name, "httpds") ?
                        "/asus-httpds6.service\n" : "/asus-httpds.service\n";
                    if (strstr(line, own)) sibling = 1;
                }
                fclose(f);
            }
            if (sibling) continue;
        }
        fprintf(stderr, "Refusing external %s PID %ld\n", comm, (long)pid);
        closedir(dir); return -1;
    }
    closedir(dir); return 0;
}
static pid_t daemon_child(const char *comm)
{
    /* /proc/.../children requires CONFIG_CHECKPOINT_RESTORE, which this
     * shipped kernel does not enable. PPid is available in /proc/PID/status. */
    DIR *dir=opendir("/proc"); struct dirent *e;
    char path[80], name[64], line[256]; long parent; pid_t found=0;
    if (!dir) return -1;
    while ((e=readdir(dir))) {
        char *end; long pid=strtol(e->d_name,&end,10); FILE *f;
        if (*end || pid<=1 || read_comm(pid,name,sizeof(name)) || strcmp(name,comm)) continue;
        snprintf(path,sizeof(path),"/proc/%ld/status",pid);
        f=fopen(path,"re"); if (!f) continue;
        while (fgets(line,sizeof(line),f))
            if (sscanf(line,"PPid: %ld",&parent)==1 && parent==(long)getpid()) {found=pid;break;}
        fclose(f); if (found) break;
    }
    closedir(dir); return found;
}
static int ready(void)
{
    const char *path = getenv("NOTIFY_SOCKET");
    struct sockaddr_un a = {.sun_family = AF_UNIX}; int fd, rc;
    const char message[] = "READY=1\nSTATUS=ASUS daemon running in its service cgroup";
    if (!path || strlen(path) >= sizeof(a.sun_path)) return -1;
    strcpy(a.sun_path, path);
    if (a.sun_path[0] == '@') a.sun_path[0] = 0;
    fd = socket(AF_UNIX, SOCK_DGRAM | SOCK_CLOEXEC, 0); if (fd < 0) return -1;
    rc = sendto(fd, message, sizeof(message)-1, MSG_NOSIGNAL,
        (struct sockaddr *)&a, offsetof(struct sockaddr_un,sun_path)+strlen(path)+(path[0]!='@'));
    close(fd); return rc == sizeof(message)-1 ? 0 : -1;
}
int main(int argc, char **argv)
{
    const struct leon_daemon *d;
    char path[96], data[8193], *fields[34], *p, *end;
    size_t used = 0; ssize_t n; struct stat st;
    struct sigaction sa = {.sa_handler = stop};
    struct timespec pause = {.tv_nsec = 50000000}, started, now;
    int fd, count = 0, pipefd[2], error = 0, status, tick, handoffs=0;
    pid_t launcher, mainpid = 0, reaped;
    cpu_set_t affinity; int have_affinity = 0;
    if (argc != 2 || geteuid() || !(d = leon_daemon_find(argv[1]))) return 2;
    snprintf(path, sizeof(path), "/run/leon-rc/%s.argv", d->name);
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
    if (fd < 0) { perror(path); return 1; }
    if (fstat(fd,&st) || !S_ISREG(st.st_mode) || st.st_uid || (st.st_mode&077) ||
        st.st_size < 4 || st.st_size > 8192) goto invalid;
    while (used < sizeof(data)) {
        n = read(fd,data+used,sizeof(data)-used);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) goto invalid;
        if (!n) break;
        used += n;
    }
    if (used != (size_t)st.st_size || data[used-1]) goto invalid;
    end = data+used;
    for (p=data; p<end; p+=strlen(p)+1) {
        if (count >= 33) goto invalid;
        fields[count++] = p;
    }
    fields[count] = NULL;
    if (count < 5 || fields[0][0] != '/' ||
        (strcmp(fields[4],d->binary) && strcmp(fields[4],d->comm))) goto invalid;
    /* The sole CPU override preserves ASUS's Samba affinity selection. */
    if (*fields[1]) {
        long cpu; char *tail;
        if (strcmp(d->name,"smbd")) goto invalid;
        cpu=strtol(fields[1],&tail,10);
        if (*tail || cpu < 0 || cpu >= CPU_SETSIZE) goto invalid;
        CPU_ZERO(&affinity); CPU_SET(cpu,&affinity); have_affinity=1;
    }
    close(fd);
    if (duplicate(d) || prctl(PR_SET_CHILD_SUBREAPER,1) || pipe2(pipefd,O_CLOEXEC)) return 1;
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGTERM,&sa,NULL) || sigaction(SIGINT,&sa,NULL)) return 1;
    launcher=fork(); if (launcher < 0) return 1;
    if (!launcher) {
        close(pipefd[0]);
        /* Match ASUS _eval's fresh session and signal dispositions. */
        sigset_t empty;
        for (int sig=1; sig<NSIG; sig++) signal(sig,SIG_DFL);
        sigemptyset(&empty);
        if (sigprocmask(SIG_SETMASK,&empty,NULL) || setsid()<0) _exit(127);
        /* init.c sysinit() uses umask(0); preserve vendor socket/file modes. */
        umask(0);
        unsetenv("NOTIFY_SOCKET");
        if ((*fields[2] && setenv("TZ",fields[2],1)) || setenv("PATH",fields[3],1)) _exit(127);
        if (!chdir(fields[0]) && (!have_affinity || !sched_setaffinity(0,sizeof(affinity),&affinity)))
            execv(d->binary,fields+4);
        error=errno;
        if (write(pipefd[1],&error,sizeof(error)) != sizeof(error)) _exit(126);
        _exit(127);
    }
    close(pipefd[1]);
    struct pollfd pf={.fd=pipefd[0],.events=POLLIN|POLLHUP};
    if (poll(&pf,1,5000) <= 0 || (n=read(pipefd[0],&error,sizeof(error))) != 0) {
        fprintf(stderr,"ASUS exec failed: %s\n",strerror(error ? error : EIO));
        return 1;
    }
    close(pipefd[0]);
    for (tick=0; tick<160 && !stopping; tick++) {
        while ((reaped=waitpid(-1,&status,WNOHANG)) > 0) {
            if (reaped==launcher && (!WIFEXITED(status) || WEXITSTATUS(status))) return 1;
        }
        if (reaped<0 && errno==ECHILD) return 1;
        /* Allow the original launcher time to complete daemonization. */
        if (tick>=6 && (mainpid=daemon_child(d->comm)) > 0) break;
        nanosleep(&pause,NULL);
    }
    if (stopping) return 0;
    if (clock_gettime(CLOCK_MONOTONIC,&started)) return 1;
    if (mainpid<=0) { fputs("No owned ASUS daemon appeared before deadline\n",stderr); return 1; }
    if (ready()) { perror("systemd notify"); return 1; }
    while (!stopping) {
        reaped=waitpid(-1,&status,0);
        if (reaped==mainpid) {
            /* Some vendor launchers daemonize only after slow hardware setup.
             * Follow a bounded double-fork chain; never adopt an unrelated PID
             * or mistake a dead daemon's helper for its replacement. HTTPD is
             * known to stay foreground, so its request workers never qualify. */
            pid_t adopted = 0;
            if (handoffs<4 && !clock_gettime(CLOCK_MONOTONIC,&now) &&
                now.tv_sec-started.tv_sec<10 && WIFEXITED(status) &&
                !WEXITSTATUS(status) && strncmp(d->name,"httpd",5))
                adopted=daemon_child(d->comm);
            if (adopted>0) { mainpid=adopted; handoffs++; continue; }
            return 1;
        }
        if (reaped<0 && errno!=EINTR) return 1;
    }
    return 0;
invalid:
    close(fd); fputs("Invalid ASUS daemon configuration\n",stderr); return 1;
}
