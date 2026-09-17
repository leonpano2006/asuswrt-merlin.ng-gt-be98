#include <assert.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
int main(void)
{
 unsigned char b[1024]={0},r[1024];size_t off=4;
 struct sockaddr_in a={.sin_family=AF_INET,.sin_port=htons(445),.sin_addr.s_addr=htonl(INADDR_LOOPBACK)};
 struct timeval tv={.tv_sec=5};int fd=socket(AF_INET,SOCK_STREAM,0);assert(fd>=0);
 assert(!setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv)));assert(!connect(fd,(void *)&a,sizeof(a)));
 memcpy(b+off,"\xffSMB",4);b[off+4]=0x72;b[off+9]=0x18;b[off+10]=0x01;b[off+11]=0x28;
 off+=32;b[off++]=0;b[off++]=12;b[off++]=0;b[off++]=2;memcpy(b+off,"NT LM 0.12",11);off+=11;b[3]=off-4;
 assert(write(fd,b,off)==(ssize_t)off);
 ssize_t n=recv(fd,r,4,MSG_WAITALL);assert(n==4);size_t len=((size_t)r[1]<<16)|(r[2]<<8)|r[3];assert(len>=35&&len<sizeof(r));
 n=recv(fd,r,len,MSG_WAITALL);assert(n==(ssize_t)len);assert(!memcmp(r,"\xffSMB",4)&&r[4]==0x72&&!r[5]&&!r[6]&&!r[7]&&!r[8]);
 assert(r[33]!=255||r[34]!=255);close(fd);puts("SMB_PROTOCOL_NEGOTIATED");return 0;
}
