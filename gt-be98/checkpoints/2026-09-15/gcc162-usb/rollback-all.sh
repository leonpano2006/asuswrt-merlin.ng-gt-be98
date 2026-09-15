#!/bin/sh
set -eu
TASK=/tmp/mnt/JFFS/gcc162-update-20260914
/bin/sh "$TASK/rollback.sh"
/bin/sh "$TASK/rollback-glibc.sh"
if [ -f "$TASK/ldd-before-2.44" ]; then
    /bin/busybox cp -p "$TASK/ldd-before-2.44" /opt/bin/ldd
fi
printf 'GCC 16.1.0 and original Entware glibc directories restored\n'
