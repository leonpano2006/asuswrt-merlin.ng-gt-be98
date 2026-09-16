#!/usr/bin/bash
set -eu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
test "$(readlink /proc/1/exe)" = /usr/lib/systemd/systemd
test "$(systemctl is-active asus-rc.service)" = active
test "$(systemctl is-active leon-local-ready.service)" = active
test -f /run/leon-systemd-trial/accepted
state=$(bcm_bootstate)
printf '%s\n' "$state"
printf '%s\n' "$state" | grep -q 'Booted Partition: First'
printf '%s\n' "$state" | grep -q 'Reboot Partition: Second'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
test -z "$(docker ps -aq --filter label=leon.test=systemd-trial)"
test -z "$(docker network ls -q --filter label=leon.test=systemd-trial)"
docker info --format 'Docker={{.ServerVersion}} driver={{.Driver}} cgroup={{.CgroupDriver}}/{{.CgroupVersion}}'
if grep -q '^br_netfilter ' /proc/modules; then exit 93; fi
test "$(cat /proc/sys/kernel/tainted)" = 4097
for iface in wl0 wl1 wl2 wl3; do
  test "$(/usr/sbin/wl -i "$iface" isup)" = 1
  # ASUS uses wlN as the radio/control interface and wlN.0 for the LAN BSS.
  test "$(readlink /sys/class/net/${iface}.0/master)" = ../br0
done
/bin/fc status
/bin/fc status | grep 'HW Acceleration <Enabled>'
systemctl --failed --no-pager
test "$(systemctl --failed --no-legend --no-pager | wc -l)" = 0
test "$(nvram get vpn_server1_state)" = 2
test "$(nvram get vpn_server1_errno)" = 0
test -d /sys/class/net/tun21
cat /proc/uptime
date -u
echo SYSTEMD_FINAL_UNCOMMITTED_STATE_PASS
