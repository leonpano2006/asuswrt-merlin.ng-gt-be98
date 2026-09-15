#!/bin/sh
set -eu
TASK=/tmp/mnt/JFFS/gcc162-update-20260914
test -d /opt/lib.glibc227-backup-20260914
test -d /opt/include.glibc227-backup-20260914
"$TASK/exchange" /opt/include /opt/include.glibc227-backup-20260914
"$TASK/exchange" /opt/lib /opt/lib.glibc227-backup-20260914
# Directory names now contain the 2.44 files; rename to avoid running twice.
/bin/busybox mv /opt/lib.glibc227-backup-20260914 /opt/lib.leon244-rolled-back-20260914
/bin/busybox mv /opt/include.glibc227-backup-20260914 /opt/include.leon244-rolled-back-20260914
if [ -f "$TASK/ldd-before-2.44" ]; then
    /bin/busybox cp -p "$TASK/ldd-before-2.44" /opt/bin/ldd
fi
/opt/lib/ld-linux-aarch64.so.1 --version | head -n 1
