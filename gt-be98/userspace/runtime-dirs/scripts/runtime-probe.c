#define _GNU_SOURCE
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void)
{
    struct stat a, b;
    struct statfs fs;
    char text[128] = {0};
    assert(readlink("/run", text, sizeof(text) - 1) == 7 && !strcmp(text, "var/run"));
    assert(!stat("/run", &a) && !stat("/var/run", &b));
    assert(a.st_ino == b.st_ino && a.st_dev == b.st_dev);
    assert(a.st_uid == 0 && a.st_gid == 0 && (a.st_mode & 07777) == 0755);
    assert(!statfs("/run", &fs) && fs.f_type == 0x01021994);
    int fd = open("/run/runtime-probe.pid", O_CREAT | O_EXCL | O_WRONLY, 0600);
    assert(fd >= 0);
    int n = snprintf(text, sizeof(text), "%ld\n", (long)getpid());
    assert(write(fd, text, n) == n && !close(fd));
    assert(!stat("/run/runtime-probe.pid", &a) && !stat("/var/run/runtime-probe.pid", &b));
    assert(a.st_ino == b.st_ino && a.st_dev == b.st_dev && b.st_size == n);
    assert(!unlink("/var/run/runtime-probe.pid"));
    assert(access("/run/runtime-probe.pid", F_OK) == -1);
    puts("LAB_RUNTIME_PID_ALIAS_TMPFS_PERMISSIONS_PASS");

    int server = socket(AF_UNIX, SOCK_STREAM, 0);
    assert(server >= 0);
    struct sockaddr_un address = {.sun_family = AF_UNIX};
    strcpy(address.sun_path, "/run/runtime-probe.sock");
    assert(!bind(server, (struct sockaddr *)&address, sizeof(address)) && !listen(server, 1));
    pid_t child = fork();
    assert(child >= 0);
    if (!child) {
        close(server);
        int client = socket(AF_UNIX, SOCK_STREAM, 0);
        strcpy(address.sun_path, "/var/run/runtime-probe.sock");
        assert(client >= 0 && !connect(client, (struct sockaddr *)&address, sizeof(address)));
        assert(write(client, "R", 1) == 1 && read(client, text, 1) == 1 && text[0] == 'K');
        close(client);
        _exit(0);
    }
    int client = accept(server, NULL, NULL);
    assert(client >= 0 && read(client, text, 1) == 1 && text[0] == 'R');
    assert(write(client, "K", 1) == 1);
    close(client);
    close(server);
    int status;
    assert(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 0);
    assert(!unlink("/var/run/runtime-probe.sock"));
    puts("LAB_RUNTIME_UNIX_SOCKET_ALIAS_PASS");
    assert(!stat("/media", &a) && S_ISDIR(a.st_mode) && (a.st_mode & 07777) == 0755);
    assert(!stat("/srv", &a) && S_ISDIR(a.st_mode) && (a.st_mode & 07777) == 0755);
    puts("LAB_RUNTIME_DIRECTORIES_PASS");
    return 0;
}
