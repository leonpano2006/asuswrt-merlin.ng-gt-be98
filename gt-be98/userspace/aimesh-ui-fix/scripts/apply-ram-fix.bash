#!/usr/bin/bash
set -eu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
# The backing executable must retain basename httpd for vendor NVRAM access.
binary=/tmp/leon-aimesh/httpd
page=/tmp/leon-aimesh/aimesh_topology.html
target=/www/aimesh/aimesh_topology.html
hash() { sha256sum "$1" | cut -d' ' -f1; }
test "$(hash "$binary")" = 2035aca8e26a14b0823e340ac08e2eddeb13d494d2595bc54e0014d4ba73cd0b
test "$(hash "$page")" = 3cef091a58002ec0b1928473531d8c41355219cc5c1d20f6dc8bc4152f8e7e4c
test "$(hash "$target")" = 61be53c86b1d1e14aca24b141837c08c5d782ee5ca880cf0af7cac71d432eea7
test "$(hash /usr/lib/arm-linux-gnueabi/libshared.so)" = 06eb9ca13f4de144c65aad7b5e013b38b5bfa128bc4b8688e474d2c6f3e7a779
case "$(hash /usr/sbin/httpd)" in
e1c6013f9e535cd76294a4acc814b5b985fb487e79dff60066b18d52cd8bf450) mount --bind "$binary" /usr/sbin/httpd ;;
2035aca8e26a14b0823e340ac08e2eddeb13d494d2595bc54e0014d4ba73cd0b) ;;
*) echo 'Unexpected HTTPD version'; exit 1 ;;
esac
test "$(systemctl is-active asus-rc)" = active
for unit in leon-aimesh-namespace-test.service leon-aimesh-basename-test.service; do
    if [ "$(systemctl show "$unit" -p LoadState --value)" != not-found ]; then
        systemctl stop "$unit"
    fi
done
broker=$(systemctl show asus-rc -p MainPID --value)
cfg=$(pidof cfg_server)
before=$(pidof httpd)
mount --bind "$page" "$target"
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
test "$(pidof cfg_server)" = "$cfg"
inode=$(stat -c %i "$binary")
for p in $after; do
    awk -v inode="$inode" '$5 == inode { found = 1 } END { exit !found }' /proc/$p/maps
done
printf 'HTTPD_BEFORE=%s\nHTTPD_AFTER=%s\nBROKER_PID=%s\nCFG_SERVER_PID=%s\n' "$before" "$after" "$broker" "$cfg"
echo AIMESH_RAM_FIX_APPLIED
