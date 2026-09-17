#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
test "$(nvram get productid)" = GT-BE98
test "$(readlink /proc/1/exe)" = /usr/lib/systemd/systemd
test "$(sha256sum /usr/sbin/rc | cut -d ' ' -f1)" = 5191c8a0bc759add07c915682375b986d89d81574535ab910beddbec24e7b87d
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
umask 077
printf 'Physical systemd257/less704 service/web/container/acceleration checks passed; firmware remains uncommitted.\n' > /run/leon-systemd-trial/accepted
stat -c 'RAM_ACCEPTANCE uid=%u mode=%a' /run/leon-systemd-trial/accepted
cat /proc/uptime
printf '%s\n' "$state"
echo RAM_ACCEPTED_FIRMWARE_UNCOMMITTED
