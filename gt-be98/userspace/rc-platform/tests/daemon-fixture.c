#define _GNU_SOURCE
#include <assert.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
static volatile sig_atomic_t stopping;
static void stop(int s) {(void)s;stopping=1;}
int main(int argc,char **argv)
{
 const char *name=strrchr(argv[0],'/');name=name?name+1:argv[0];
 assert(argc==3);const char *id=argv[1];int mode=atoi(argv[2]);
 prctl(PR_SET_NAME,name);
 if(strcmp(id,"external")){
 assert(getsid(0)==getpid());
 mode_t old=umask(0);assert(old==0);
 struct sigaction pipe_action;assert(!sigaction(SIGPIPE,NULL,&pipe_action));assert(pipe_action.sa_handler==SIG_DFL);
 }
 if(mode==3) sleep(1);
 if(mode==2 || mode==3){pid_t p=fork();assert(p>=0);if(p)return 0;assert(setsid()>0);p=fork();assert(p>=0);if(p)_exit(0);}
 signal(SIGTERM,stop);signal(SIGINT,stop);
 char path[128];snprintf(path,sizeof(path),"/run/fixture-%s",id);FILE *f=fopen(path,"w");assert(f);fprintf(f,"%d\n",getpid());fclose(f);
 if(!strcmp(id,"notification")){pid_t p=fork();assert(p>=0);if(!p){prctl(PR_SET_NAME,"nt_center");while(!stopping)pause();return 0;}}
 while(!stopping)pause();
 return 0;
}
