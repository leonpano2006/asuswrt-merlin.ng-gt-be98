/* Offline probe linked only to a test-double provider; no flash or reboot calls. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
int commit(int, char *), setBootImageState(int), setImgValidStatus(int, int *);
int setImgSeqNum(int, int), setNandMetadata(char *, int, int), setEmmcMetadata(char *, int, int);

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "--child"))
        return getenv("LD_PRELOAD") || setBootImageState(0) != 91;
    if (getpid() <= 1 || strcmp(argv[0], "/sbin/init") || getenv("LD_PRELOAD")) return 2;
    char flag = 0;
    if (commit(1, &flag) != 0 || flag != '1') return 3;
    flag = '1';
    if (commit(2, &flag) != -1) return 4;
    flag = '0';
    if (commit(1, &flag) != -1) return 5;
    int status = 1;
    if (setBootImageState(0) != -1 || setImgValidStatus(1, &status) != -1 ||
        setImgSeqNum(1, 99) != -1 || setNandMetadata(NULL, 0, 0) != -1 ||
        setEmmcMetadata(NULL, 0, 0) != -1) return 6;
    pid_t child = fork();
    if (child == 0) {
        execl("/usr/libexec/leon-systemd-guardcheck", "leon-systemd-guardcheck", "--child", NULL);
        _exit(7);
    }
    if (child < 0 || waitpid(child, &status, 0) != child ||
        !WIFEXITED(status) || WEXITSTATUS(status) != 0) return 8;
    puts("LAB_SYSTEMD_ARMEL_GUARD_SERVICE_PASS");
    return 0;
}
