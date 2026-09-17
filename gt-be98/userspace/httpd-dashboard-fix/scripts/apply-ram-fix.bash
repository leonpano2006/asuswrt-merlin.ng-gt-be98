#!/usr/bin/bash
set -eu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
library=/usr/lib/arm-linux-gnueabi/libshared.so
fixed=/tmp/leon-libshared-fixed.so
test "$(sha256sum "$library" | cut -d' ' -f1)" = 6e604a860fc2752e28238e34c7886311d9751d5802f31fc6dda056eea6fa3b5c
test "$(sha256sum "$fixed" | cut -d' ' -f1)" = 06eb9ca13f4de144c65aad7b5e013b38b5bfa128bc4b8688e474d2c6f3e7a779
test "$(systemctl is-active asus-rc)" = active
systemctl stop leon-httpd-fixed-test
broker=$(systemctl show asus-rc -p MainPID --value)
before=$(pidof httpd)
mount --bind "$fixed" "$library"
/sbin/service restart_httpd
fresh=0
for i in $(seq 1 40); do
    after=$(pidof httpd || true)
    fresh=1
    for old in $before; do
        case " $after " in *" $old "*) fresh=0;; esac
    done
    test -n "$after" || fresh=0
    if [ "$fresh" = 1 ]; then break; fi
    sleep 1
done
test "$fresh" = 1
test "$(systemctl show asus-rc -p MainPID --value)" = "$broker"
test "$(systemctl is-active asus-rc)" = active
inode=$(stat -c %i "$fixed")
for p in $after; do
    awk -v inode="$inode" -v library="$library" '$5 == inode && $6 == library { found = 1; print } END { exit !found }' /proc/$p/maps
done
date -u
printf 'HTTPD_BEFORE=%s\nHTTPD_AFTER=%s\nBROKER_PID=%s\n' "$before" "$after" "$broker"
echo HTTPD_RAM_FIX_APPLIED
