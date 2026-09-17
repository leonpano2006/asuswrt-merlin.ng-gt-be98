/* A cron job with a deterministic SIGTERM receipt; no fork inside its handler.
 * The previous shell trap could launch /usr/bin/echo while systemd was still
 * enumerating the terminating cgroup, so that echo could itself receive TERM. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>
static void stopped(int sig)
{
 (void)sig;
 int fd=open("/run/cron-child-terminated",O_WRONLY|O_CREAT|O_TRUNC,0600);
 if(fd<0)_exit(1);
 ssize_t n=write(fd,"terminated\n",11);
 if(close(fd)||n!=11)_exit(1);
 _exit(0);
}
int main(void)
{
 struct sigaction sa={.sa_handler=stopped};sigemptyset(&sa.sa_mask);assert(!sigaction(SIGTERM,&sa,NULL));
 FILE *f=fopen("/run/cron-child-pid","w");assert(f);fprintf(f,"%ld\n",(long)getpid());assert(!fclose(f));
 for(;;)pause();
}
