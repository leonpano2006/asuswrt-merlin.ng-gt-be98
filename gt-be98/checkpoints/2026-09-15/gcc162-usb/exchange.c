#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <unistd.h>
#ifndef RENAME_EXCHANGE
#define RENAME_EXCHANGE (1 << 1)
#endif
int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: exchange path1 path2\n");
        return 2;
    }
    if (syscall(SYS_renameat2, AT_FDCWD, argv[1], AT_FDCWD, argv[2], RENAME_EXCHANGE)) {
        perror("renameat2(RENAME_EXCHANGE)");
        return 1;
    }
    return 0;
}
