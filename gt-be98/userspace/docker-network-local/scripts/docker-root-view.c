#define _GNU_SOURCE
#include <errno.h>
#include <limits.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>

/* Build a root view only in the new Docker process's mount namespace.
 * /usr is recursive to preserve the USB-backed /usr/local submount.
 * /var is deliberately NON-recursive because it contains this view's mount.
 * No network/PID/user namespace is changed; host services retain their root.
 * Namespace teardown releases these mounts without changing host mount state.
 */
static const char *view = "/var/run/leon-docker/root-view";
static void die(const char *what) { perror(what); exit(1); }
static void directory(const char *p, mode_t mode) {
    if (mkdir(p,mode) && errno!=EEXIST) die(p);
    struct stat s;
    if (lstat(p,&s) || !S_ISDIR(s.st_mode)) { errno=ENOTDIR; die(p); }
}
int main(int argc,char **argv) {
    struct utsname u;
    if (geteuid()!=0 || uname(&u) || strcmp(u.release,"4.19.294") || (strncmp(u.version,"#35 ",4) && strncmp(u.version,"#36 ",4))) {
        fputs("Requires verified root on GT-BE98 kernel #35 or #36\n",stderr); return 90;
    }
    if (argc!=2 || (strcmp(argv[1],"--probe") && strcmp(argv[1],"--daemon"))) return 2;
    if (unshare(CLONE_NEWNS)) die("unshare mount namespace");
    if (mount(NULL,"/",NULL,MS_REC|MS_PRIVATE,NULL)) die("private propagation");
    directory(view,0755);
    if (mount("leon-docker-root-view",view,"tmpfs",MS_NOSUID|MS_NODEV,"mode=755,size=256k")) die("mount root view");
    const char *dirs[]={"bin","bootfs","cifs1","cifs2","data","dev","jffs","lib","mmc","proc","rom","sbin","sys","sysroot","tmp","usr","var","webs","www",NULL};
    char src[PATH_MAX],dst[PATH_MAX];
    for (unsigned i=0;dirs[i];i++) {
        snprintf(src,sizeof(src),"/%s",dirs[i]);
        snprintf(dst,sizeof(dst),"%s/%s",view,dirs[i]);
        directory(dst,0755);
        unsigned long flags=MS_BIND;
        if (!strcmp(dirs[i],"dev") || !strcmp(dirs[i],"sys") || !strcmp(dirs[i],"tmp") || !strcmp(dirs[i],"usr")) flags|=MS_REC;
        if (mount(src,dst,NULL,flags,NULL)) die(src);
    }
    const char *links[]={"debug","etc","home","mnt","opt","root",NULL};
    char target[PATH_MAX];
    for (unsigned i=0;links[i];i++) {
        snprintf(src,sizeof(src),"/%s",links[i]);
        snprintf(dst,sizeof(dst),"%s/%s",view,links[i]);
        ssize_t n=readlink(src,target,sizeof(target)-1);
        if (n<0 || n==(ssize_t)sizeof(target)-1) die("read root symlink");
        target[n]=0;
        if (symlink(target,dst)) die("copy root symlink");
    }
    snprintf(dst,sizeof(dst),"%s/run",view);
    if (symlink("var/run",dst)) die("create private /run");
    if (chdir(view) || chroot(".") || chdir("/")) die("enter Docker root view");
    if (!strcmp(argv[1],"--probe")) {
        const char *paths[]={"/run","/var/run","/proc/self","/sys/fs/cgroup/devices/devices.list","/dev/null","/dev/pts","/jffs/docker/config/daemon.json","/opt","/etc/resolv.conf",NULL};
        struct stat s;
        for (unsigned i=0;paths[i];i++) if (stat(paths[i],&s)) die(paths[i]);
        puts("ROOT_VIEW_PROBE_PASS"); return 0;
    }
    execl("/usr/local/bin/dockerd","dockerd","--config-file=/jffs/docker/config/daemon.json",(char *)NULL);
    die("exec dockerd");
}
