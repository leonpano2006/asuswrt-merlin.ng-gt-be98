/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <mntent.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static int logfd = -1;
static void note(const char *message)
{
    dprintf(2, "LEON_SYSTEMD_TRIAL: %s\n", message);
    if (logfd >= 0) dprintf(logfd, "LEON_SYSTEMD_TRIAL: %s\n", message);
}
static void fallback(void)
{
    note("Rebooting to the already committed fallback; no boot metadata write");
    sync(); reboot(RB_AUTOBOOT);
    for (;;) pause();
}
static int mount_once(const char *source, const char *target, const char *type,
                      unsigned long flags, const char *options)
{
    FILE *stream = setmntent("/proc/self/mounts", "r");
    struct mntent *entry;
    if (stream) {
        while ((entry = getmntent(stream))) if (!strcmp(entry->mnt_dir, target)) {
            int same = !strcmp(entry->mnt_type, type);
            endmntent(stream); errno = EBUSY; return same ? 0 : -1;
        }
        endmntent(stream);
    }
    return mount(source, target, type, flags, options);
}
static void require_mount(const char *source, const char *target, const char *type,
                          unsigned long flags, const char *options)
{
    if (!mount_once(source, target, type, flags, options)) return;
    perror(target); note("Required early mount failed"); sleep(10); fallback();
}
static double monotonic(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec + (double)t.tv_nsec / 1000000000.;
}
static void monitor(int lab)
{
    char buffer[8192]; size_t written = 0;
    int kmsg = open("/dev/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    double deadline = monotonic() + 900.;
    prctl(PR_SET_NAME, "leon-trialmon", 0, 0, 0);
    while (monotonic() < deadline) {
        struct stat st;
        if (!lstat("/run/leon-systemd-trial/accepted", &st) && S_ISREG(st.st_mode) &&
            st.st_uid == 0 && !(st.st_mode & 0022)) {
            note("Trial accepted in RAM; firmware remains uncommitted"); _exit(0);
        }
        if (kmsg >= 0) for (int count = 0; count < 128; count++) {
            ssize_t n = read(kmsg, buffer, sizeof(buffer));
            if (n < 0) { if (errno == EPIPE) continue; break; }
            if (!n) break;
            if (logfd >= 0 && written < 2 * 1024 * 1024) {
                (void)write(logfd, buffer, (size_t)n); written += (size_t)n;
            }
        }
        sleep(1);
    }
    note("Trial deadline expired without RAM acceptance");
    if (lab) { note("Lab deadline does not alter hardware"); _exit(1); }
    pid_t child = fork();
    if (!child) { execl("/usr/bin/systemctl", "systemctl", "--no-block", "reboot", (char *)NULL); _exit(127); }
    sleep(30); fallback();
}
int main(void)
{
    char cmdline[4096] = {0}; int fd, lab, status;
    pid_t pid;
    if (getpid() != 1) return 2;
    umask(0022);
    setenv("PATH", "/usr/sbin:/usr/bin:/sbin:/bin", 1);
    unsetenv("LD_LIBRARY_PATH"); unsetenv("LD_PRELOAD");
    require_mount("proc", "/proc", "proc", 0, NULL);
    require_mount("sysfs", "/sys", "sysfs", 0, NULL);
    require_mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
    fd = open("/proc/cmdline", O_RDONLY | O_CLOEXEC);
    if (fd >= 0) { (void)read(fd, cmdline, sizeof(cmdline)-1); close(fd); }
    lab = strstr(cmdline, "leon_systemd_lab=1") != NULL;
    if (lab && !access("/sys/class/ubi/ubi0", F_OK)) return 3;
    require_mount("tmpfs", "/tmp", "tmpfs", MS_NOSUID, "mode=1777");
    require_mount("tmpfs", "/run", "tmpfs", MS_NOSUID | MS_NODEV, "mode=0755");
    require_mount("tmpfs", "/var", "tmpfs", MS_NOSUID, "mode=0755");
    mkdir("/dev/pts", 0755); mkdir("/dev/shm", 01777);
    require_mount("devpts", "/dev/pts", "devpts", 0, "mode=0620,ptmxmode=0666");
    require_mount("tmpfs", "/dev/shm", "tmpfs", MS_NOSUID | MS_NODEV, "mode=1777");
    mkdir("/tmp/mnt", 0755);
    require_mount("tmpfs", "/tmp/mnt", "tmpfs", MS_NOSUID, "size=128k,mode=0755");
    mkdir("/sys/kernel/debug", 0755);
    (void)mount_once("debugfs", "/sys/kernel/debug", "debugfs", 0, NULL);
    if (!lab) {
        require_mount("ubi:data", "/data", "ubifs", 0, NULL);
        mkdir("/data/leon-systemd-trial", 0700);
        logfd = open("/data/leon-systemd-trial/boot.log", O_WRONLY | O_CREAT | O_APPEND | O_DSYNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    }
    note(lab ? "Offline early-init rehearsal" : "Hardware early-init start");
    fd = open("/proc/sys/kernel/panic", O_WRONLY | O_CLOEXEC);
    if (fd >= 0) { (void)write(fd, "10\n", 3); close(fd); }
    pid = fork();
    if (!pid) monitor(lab);
    if (pid < 0) { note("Cannot start trial monitor"); fallback(); }
    pid = fork();
    if (!pid) { execl("/bin/sh", "sh", "/usr/libexec/leon-systemd-prepare", lab ? "lab" : "hardware", (char *)NULL); _exit(127); }
    if (pid < 0 || waitpid(pid, &status, 0) != pid || !WIFEXITED(status) || WEXITSTATUS(status)) {
        note("Early configuration failed"); sleep(10); fallback();
    }
    note("Executing systemd as PID 1");
    execl("/usr/lib/systemd/systemd", "systemd", "--system",
          lab ? "--unit=leon-boot-test.target" : "--unit=leon-router.target",
          lab ? "--log-target=console" : "--log-target=kmsg", "--log-level=info", "--show-status=yes", (char *)NULL);
    perror("exec systemd"); sleep(10); fallback();
}
