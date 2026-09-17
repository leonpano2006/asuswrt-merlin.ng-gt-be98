#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
test "$(nvram get productid)" = GT-BE98
test "$(readlink /proc/1/exe)" = /usr/lib/systemd/systemd
grep -q '3006.102.9-beta1-leon10' /usr/share/leon-upstream.json
test "$(sha256sum /usr/sbin/rc | cut -d' ' -f1)" = cf121058ede3661d8b5a9f3bc3e8aed2850d533205b71ccf20bcf3a46c221981
test "$(sha256sum /usr/sbin/httpd | cut -d' ' -f1)" = 2035aca8e26a14b0823e340ac08e2eddeb13d494d2595bc54e0014d4ba73cd0b
for name in rc sshd httpd httpds cfg-server acsd2; do test "$(systemctl is-active asus-$name.service)" = active; done
test "$(systemctl show asus-acsd2.service -p MainPID --value)" = 4327
test "$(systemctl show asus-acsd2.service -p NRestarts --value)" = 1
test "$(systemctl --failed --no-legend --no-pager | wc -l)" = 0
for iface in wl0 wl1 wl2 wl3; do test "$(wl -i "$iface" isup)" = 1; done
/bin/fc status | grep 'HW Acceleration <Enabled>'
test -z "$(docker ps -q)"
state=$(bcm_bootstate)
printf '%s\n' "$state" | grep -q 'Booted Partition: First'
printf '%s\n' "$state" | grep -q 'Reboot Partition: Second'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
umask 077
printf 'leon10 physical trial accepted in RAM after API/browser, radios, hardware flow counters, service ownership, USB/logging and Docker tests. One stable acsd2 initialization restart remains recorded. Firmware not committed.\n' > /run/leon-systemd-trial/accepted
stat -c 'RAM_ACCEPTANCE uid=%u mode=%a' /run/leon-systemd-trial/accepted
cat /proc/uptime
printf '%s\n' "$state"
date -u
echo RAM_ACCEPTED_FIRMWARE_UNCOMMITTED
