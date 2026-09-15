#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
int main(int argc,char **argv)
{
    if(argc!=5)return 2;
    uid_t uid=(uid_t)strtoul(argv[1],0,10);int want_read=atoi(argv[3]),want_write=atoi(argv[4]);
    if(!uid||setgroups(0,0)||setgid(uid)||setuid(uid)){perror("drop test credentials");return 3;}
    int fd=open(argv[2],O_RDONLY);int rd=fd>=0;if(rd)close(fd);else if(errno!=EACCES&&errno!=EPERM){perror("read");return 4;}
    fd=open(argv[2],O_WRONLY);int wr=fd>=0;if(wr)close(fd);else if(errno!=EACCES&&errno!=EPERM){perror("write");return 5;}
    printf("ACL_ACCESS uid=%lu read=%d write=%d expected=%d/%d\n",(unsigned long)uid,rd,wr,want_read,want_write);
    return rd==want_read&&wr==want_write?0:6;
}
