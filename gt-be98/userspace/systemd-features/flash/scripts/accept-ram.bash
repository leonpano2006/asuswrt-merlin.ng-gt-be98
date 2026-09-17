#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
test "$(nvram get productid)" = GT-BE98
test "$(readlink /proc/1/exe)" = /usr/lib/systemd/systemd
test "$(sha256sum /usr/sbin/rc | cut -d ' ' -f1)" = ca786145c19101bbfd4bb540aff3fbd3895d7dc47a2a7d476319d0a4009226a8
test "$(sha256sum /usr/sbin/httpd | cut -d ' ' -f1)" = e1c6013f9e535cd76294a4acc814b5b985fb487e79dff60066b18d52cd8bf450
if awk '$2=="/usr/sbin/httpd"{found=1}END{exit !found}' /proc/mounts; then echo "Unexpected live HTTPD bind" >&2; exit 92; fi
for unit in asus-rc.service asus-haveged.service asus-crond.service asus-infosvr.service asus-cron-cleanup.service leon-local-ready.service; do test "$(systemctl is-active "$unit")" = active; done
for iface in wl0 wl1 wl2 wl3; do test "$(wl -i "$iface" isup)" = 1; done
/bin/fc status | grep 'HW Acceleration <Enabled>'
test "$(systemctl --failed --no-legend --no-pager | wc -l)" = 0
state=$(bcm_bootstate)
printf '%s\n' "$state" | grep -q 'Booted Partition: First'
printf '%s\n' "$state" | grep -q 'Reboot Partition: Second'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
test "$(readlink /usr/lib/arm-linux-gnueabihf)" = /tmp/mnt/JFFS/system-libs/gt-be98/8da410f090d92cff/arm-linux-gnueabihf
/usr/bin/grep -q '3006.102.9-beta1-leon7' /usr/share/leon-upstream.json
/lib/ld-linux-armhf.so.3 --version >/dev/null
/usr/libexec/openssl4 version | grep 'OpenSSL 4'
/usr/bin/zstd --version
/usr/gnu/bin/sqlite3 :memory: 'select sqlite_version();'
test "$(systemctl --version | head -1)" = 'systemd 257 (257.13-gt-be98-leon7)'
for feature in OPENSSL CURL ZLIB ZSTD BLKID; do systemctl --version | grep -q "+$feature"; done
/usr/sbin/sysctl --version | grep -q 'procps-ng 4.0.7'
test -f /run/leon7-live-features-passed
umask 077
printf 'Physical leon7 service/web/runtime/USB/acceleration acceptance checks passed; firmware remains uncommitted.\n' > /run/leon-systemd-trial/accepted
stat -c 'RAM_ACCEPTANCE uid=%u mode=%a' /run/leon-systemd-trial/accepted
cat /proc/uptime
printf '%s\n' "$state"
echo RAM_ACCEPTED_FIRMWARE_UNCOMMITTED
