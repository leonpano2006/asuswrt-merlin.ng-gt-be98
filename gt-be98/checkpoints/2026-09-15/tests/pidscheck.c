#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define ROOT "/sys/fs/cgroup"

static void require(int ok, const char *what)
{
	if (!ok) {
		fprintf(stderr, "LAB_FAIL %s errno=%d\n", what, errno);
		exit(1);
	}
}

static void put(const char *dir, const char *file, const char *value)
{
	char path[256];
	int fd;
	snprintf(path, sizeof(path), "%s/%s", dir, file);
	fd = open(path, O_WRONLY | O_CLOEXEC);
	require(fd >= 0, path);
	require(write(fd, value, strlen(value)) == (ssize_t)strlen(value), path);
	close(fd);
}

static long number(const char *dir, const char *file)
{
	char path[256], buf[128];
	int fd;
	ssize_t n;
	snprintf(path, sizeof(path), "%s/%s", dir, file);
	fd = open(path, O_RDONLY | O_CLOEXEC);
	require(fd >= 0, path);
	n = read(fd, buf, sizeof(buf) - 1);
	close(fd);
	require(n > 0, path);
	buf[n] = 0;
	return strtol(buf, NULL, 10);
}

static void count_is(const char *dir, long expected)
{
	int i;
	for (i = 0; i < 1000; i++) {
		if (number(dir, "pids.current") == expected)
			return;
		usleep(1000);
	}
	require(0, "pids.current did not settle");
}

static void move_self(const char *dir)
{
	char pid[32];
	snprintf(pid, sizeof(pid), "%ld", (long)getpid());
	put(dir, "cgroup.procs", pid);
}

static void wait_ok(pid_t child)
{
	int status;
	require(child > 0, "fork");
	require(waitpid(child, &status, 0) == child, "waitpid");
	require(WIFEXITED(status) && WEXITSTATUS(status) == 0, "child result");
}

static void *thread_hold(void *arg)
{
	char c;
	int fd = *(int *)arg;
	(void)read(fd, &c, 1);
	return NULL;
}

static void limit_body(const char *dir)
{
	int pipes[2], rc;
	pid_t held, extra;
	pthread_t first, second;
	char c = 'x';
	move_self(dir);
	count_is(dir, 1);
	require(pipe(pipes) == 0, "pipe");
	held = fork();
	if (!held) {
		close(pipes[1]);
		(void)read(pipes[0], &c, 1);
		_exit(0);
	}
	require(held > 0, "first allowed fork");
	count_is(dir, 2);
	errno = 0;
	extra = fork();
	if (!extra)
		_exit(0);
	require(extra == -1 && errno == EAGAIN, "pids limit must reject fork");
	require(write(pipes[1], &c, 1) == 1, "release child");
	wait_ok(held);
	count_is(dir, 1);
	extra = fork();
	if (!extra)
		_exit(0);
	wait_ok(extra);
	count_is(dir, 1);

	require(pthread_create(&first, NULL, thread_hold, &pipes[0]) == 0, "first allowed thread");
	count_is(dir, 2);
	rc = pthread_create(&second, NULL, thread_hold, &pipes[0]);
	require(rc == EAGAIN, "pids limit must also reject thread");
	require(write(pipes[1], &c, 1) == 1, "release thread");
	require(pthread_join(first, NULL) == 0, "join thread");
	count_is(dir, 1);
	close(pipes[0]);
	close(pipes[1]);
}

static void check_limit(const char *dir)
{
	pid_t child = fork();
	if (!child) {
		limit_body(dir);
		_exit(0);
	}
	wait_ok(child);
	count_is(dir, 0);
}

static void lifecycle(void)
{
	char dir[256];
	int i, j;
	for (i = 0; i < 50; i++) {
		pid_t child;
		snprintf(dir, sizeof(dir), ROOT "/cycle-%d", i);
		require(mkdir(dir, 0755) == 0, "lifecycle mkdir");
		put(dir, "pids.max", "4");
		child = fork();
		if (!child) {
			move_self(dir);
			for (j = 0; j < 5; j++) {
				pid_t next = fork();
				if (!next)
					_exit(0);
				wait_ok(next);
			}
			move_self(ROOT);
			_exit(0);
		}
		wait_ok(child);
		count_is(dir, 0);
		require(rmdir(dir) == 0, "lifecycle rmdir");
	}
}

static void namespaces(void)
{
	pid_t child = fork();
	if (!child) {
		pid_t inner;
		require(unshare(CLONE_NEWUTS | CLONE_NEWIPC | CLONE_NEWNS | CLONE_NEWNET | CLONE_NEWPID) == 0,
			"unshare existing namespaces");
		require(sethostname("leon-qemu", 9) == 0, "UTS hostname");
		inner = fork();
		if (!inner)
			_exit(getpid() == 1 ? 0 : 1);
		wait_ok(inner);
		_exit(0);
	}
	wait_ok(child);
}

int main(void)
{
	setbuf(stdout, NULL);
	require(getppid() == 1 && access("/QEMU_LAB_GUEST", R_OK) == 0, "QEMU initramfs guard");
	put(ROOT, "cgroup.subtree_control", "+pids");
	require(mkdir(ROOT "/limit", 0755) == 0, "limit mkdir");
	put(ROOT "/limit", "pids.max", "2");
	check_limit(ROOT "/limit");
	require(rmdir(ROOT "/limit") == 0, "limit cleanup");
	puts("LAB_PASS pids_fork_thread_limit_and_release");

	require(mkdir(ROOT "/parent", 0755) == 0, "parent mkdir");
	put(ROOT "/parent", "pids.max", "2");
	put(ROOT "/parent", "cgroup.subtree_control", "+pids");
	require(mkdir(ROOT "/parent/child", 0755) == 0, "nested mkdir");
	put(ROOT "/parent/child", "pids.max", "32");
	check_limit(ROOT "/parent/child");
	require(rmdir(ROOT "/parent/child") == 0, "nested cleanup");
	require(rmdir(ROOT "/parent") == 0, "parent cleanup");
	puts("LAB_PASS pids_hierarchical_limit");
	lifecycle();
	puts("LAB_PASS cgroup_50_create_migrate_250_fork_remove_cycles");
	namespaces();
	puts("LAB_PASS uts_ipc_mount_net_pid_namespaces");
	return 0;
}
