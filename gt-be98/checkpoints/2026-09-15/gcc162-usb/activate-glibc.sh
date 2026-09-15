#!/bin/sh
set -eu
TASK=/tmp/mnt/JFFS/gcc162-update-20260914
SWAP=$TASK/exchange
LIB=/opt/lib.leon244-20260914
INC=/opt/include.leon244-20260914
test -d "$LIB"
test -d "$INC"
test ! -e /opt/lib.glibc227-backup-20260914
test ! -e /opt/include.glibc227-backup-20260914
grep -q ENTWARE244_PRECHECK_PASSED "$TASK/entware-precheck.log"
grep -q 'LOADER_SCAN ok=88 failed=0' "$TASK/loader-scan.log"
lib_changed=0
inc_changed=0
undo() {
    status=$?
    if [ "$status" -ne 0 ]; then
        if [ "$inc_changed" = 1 ]; then "$SWAP" /opt/include "$INC"; fi
        if [ "$lib_changed" = 1 ]; then "$SWAP" /opt/lib "$LIB"; fi
        printf 'glibc activation failed; original directories restored\n' >&2
    fi
}
trap undo EXIT
"$SWAP" /opt/lib "$LIB"
lib_changed=1
"$SWAP" /opt/include "$INC"
inc_changed=1
/opt/bin/bash -c 'echo ENTWARE_LIVE_BASH_OK'
/opt/bin/perl -MSocket -e 'my ($e,@r)=Socket::getaddrinfo("example.com",80); die $e if $e; die "empty" unless @r; print "ENTWARE_LIVE_DNS_OK\n";'
/opt/lib/ld-linux-aarch64.so.1 --version | head -n 1
# Hold packages owning libc runtime and development files, preventing a future
# ordinary opkg upgrade from restoring the 2.27 copies and headers.
/opt/bin/opkg flag hold libc libpthread librt gcc
trap - EXIT
/bin/busybox mv "$LIB" /opt/lib.glibc227-backup-20260914
/bin/busybox mv "$INC" /opt/include.glibc227-backup-20260914
printf 'GLIBC244_ACTIVATED\n'
