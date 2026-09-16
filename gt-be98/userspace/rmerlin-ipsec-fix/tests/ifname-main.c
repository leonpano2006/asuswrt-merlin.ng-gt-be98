#include <assert.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

__attribute__((noinline)) static void old_copy(const char *name)
{
    char interface[4];
    strcpy(interface, name);
    assert(write(STDOUT_FILENO, interface, strlen(interface)) >= 0);
}

int main(int argc, char **argv)
{
    const char *valid[] = {"", "br0", "eth0", "ppp0", "bond0", "vlan4094", "abcdefghijklmno"};
    const char *invalid[] = {NULL, "abcdefghijklmnop", "abcdefghijklmnopq"};
    struct { unsigned char before[16]; char name[IFNAMSIZ]; unsigned char after[16]; } buf;
    struct rlimit limit = {0, 0};
    assert(setrlimit(RLIMIT_CORE, &limit) == 0);
    pid_t pid = fork();
    assert(pid >= 0);
    if (!pid) { old_copy(argc > 1 ? argv[1] : "eth0"); _exit(0); }
    int status;
    assert(waitpid(pid, &status, 0) == pid);
    assert(WIFSIGNALED(status) && WTERMSIG(status) == SIGABRT);
    puts("LAB_IPSEC_OLD_ETH0_OVERFLOW_REPRODUCED");
    for (unsigned i = 0; i < sizeof(valid) / sizeof(valid[0]); ++i) {
        memset(&buf, 0x5a, sizeof(buf));
        assert(ipsec_copy_ifname(buf.name, valid[i]) == 0);
        assert(strcmp(buf.name, valid[i]) == 0);
        for (unsigned j = 0; j < 16; ++j) assert(buf.before[j] == 0x5a && buf.after[j] == 0x5a);
    }
    for (unsigned i = 0; i < sizeof(invalid) / sizeof(invalid[0]); ++i) {
        memset(&buf, 0x5a, sizeof(buf));
        assert(ipsec_copy_ifname(buf.name, invalid[i]) == -1);
        assert(buf.name[0] == 0);
        for (unsigned j = 0; j < 16; ++j) assert(buf.before[j] == 0x5a && buf.after[j] == 0x5a);
    }
    puts("LAB_IPSEC_IFNAME_BOUNDARIES_PASS");
    return 0;
}
