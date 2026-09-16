/* Offline loopback DNS regression for the actual staged dnsmasq. */
#include <arpa/inet.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
static unsigned be16(const unsigned char *p) { return (p[0] << 8) | p[1]; }
static size_t name_end(const unsigned char *b, size_t n, size_t p) {
    while (p < n && b[p]) {
        if ((b[p] & 0xc0) == 0xc0) return p + 2 <= n ? p + 2 : 0;
        if (b[p] > 63 || p + 1 + b[p] > n) return 0;
        p += 1 + b[p];
    }
    return p < n ? p + 1 : 0;
}
int main(void) {
    unsigned char q[] = {0x53,0x98,1,0,0,1,0,0,0,0,0,0,8,'u','p','s','t','r','e','a','m',4,'t','e','s','t',0,0,1,0,1};
    unsigned char b[2048]; struct sockaddr_in a = {.sin_family=AF_INET,.sin_port=htons(1053),.sin_addr={htonl(INADDR_LOOPBACK)}};
    struct timeval t = {.tv_sec=3}; int s=socket(AF_INET,SOCK_DGRAM,0); assert(s>=0);
    assert(!setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,&t,sizeof(t)));
    assert(sendto(s,q,sizeof(q),0,(void *)&a,sizeof(a))==(ssize_t)sizeof(q));
    ssize_t z=recv(s,b,sizeof(b),0); close(s); assert(z>=12); size_t n=(size_t)z;
    assert(be16(b)==0x5398 && !(b[3]&15) && be16(b+4)==1 && be16(b+6)>0);
    size_t p=name_end(b,n,12); assert(p && p+4<=n); p+=4;
    for (unsigned i=0;i<be16(b+6);i++) {
        p=name_end(b,n,p); assert(p && p+10<=n); unsigned typ=be16(b+p), cls=be16(b+p+2), len=be16(b+p+8); p+=10;
        assert(p+len<=n);
        if (typ==1 && cls==1 && len==4 && !memcmp(b+p,"\xc0\x00\x02\x09",4)) { puts("LAB_DNS_LOOPBACK_QUERY_PASS"); return 0; }
        p+=len;
    }
    return 1;
}
