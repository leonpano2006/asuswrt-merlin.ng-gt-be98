/* QEMU test double. It has no filesystem, device, flash or reboot access. */
int commit(int p,char *f) { if (!*f) { *f=p==1?'1':'0';return 0; } return 91; }
int setBootImageState(int s) { (void)s;return 91; }
int setImgValidStatus(int p,int *s) { (void)p;(void)s;return 91; }
int setImgSeqNum(int p,int s) { (void)p;(void)s;return 91; }
int setNandMetadata(char *d,int s,int i) { (void)d;(void)s;(void)i;return 91; }
int setEmmcMetadata(char *d,int s,int i) { (void)d;(void)s;(void)i;return 91; }
