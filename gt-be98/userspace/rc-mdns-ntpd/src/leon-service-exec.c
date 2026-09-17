/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

/* Execute only these two foreground daemons with the manager's literal argv.
 * No shell, environment expansion, host NVRAM parser or proprietary library. */
int main(int argc, char **argv)
{
    char data[8193], path[96], *args[32], *end, *p;
    const char *binary, *foreground;
    size_t used = 0;
    struct stat st;
    ssize_t n;
    int fd, count = 0, seen_foreground = 0;

    if (argc != 2 || geteuid() != 0) return 2;
    if (!strcmp(argv[1], "ntpd")) {
        binary = "/usr/sbin/ntp"; foreground = "-n";
    } else if (!strcmp(argv[1], "mdns")) {
        binary = "/usr/sbin/avahi-daemon"; foreground = "-s";
    } else return 2;
    snprintf(path, sizeof(path), "/run/leon-rc/%s.argv", argv[1]);
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
    if (fd < 0) { perror(path); return 1; }
    if (fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_uid != 0 ||
        (st.st_mode & 077) || st.st_size < 1 || st.st_size > 8192) goto invalid;
    while (used < sizeof(data)) {
        n = read(fd, data + used, sizeof(data) - used);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) goto invalid;
        if (!n) break;
        used += n;
    }
    if (used != (size_t)st.st_size || data[used - 1]) goto invalid;
    end = data + used;
    for (p = data; p < end; p += strlen(p) + 1) {
        if (count >= 31) goto invalid;
        args[count++] = p;
        if (!strcmp(p, foreground)) seen_foreground = 1;
        if (!strcmp(argv[1], "mdns") &&
            (!strcmp(p, "-D") || !strcmp(p, "--daemonize"))) goto invalid;
    }
    args[count] = NULL;
    if (strcmp(args[0], binary) || !seen_foreground) goto invalid;
    close(fd);
    execv(binary, args);
    perror(binary);
    return 1;
invalid:
    close(fd);
    fputs("Invalid rc service argument file\n", stderr);
    return 1;
}
