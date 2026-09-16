#!/usr/bin/bash
set -eu
work=/tmp/leon-ubuntu-verify
date -u
uname -a
cat /proc/uptime
bcm_bootstate
for path in /sys/class/ubi/ubi0/avail_eraseblocks /proc/sys/kernel/tainted; do
  printf '%s=' "$path"
  cat "$path"
done
grep ' /usr/local ' /proc/self/mountinfo
ls -ld /usr/local /usr/local/bin/docker
sha256sum /usr/lib/arm-linux-gnueabi/libnvram.so
/usr/local/bin/docker ps -a --filter label=leon.test=ubuntu-multiarch
/usr/local/bin/docker network ls --filter label=leon.test=ubuntu-multiarch
test -z "$(/usr/local/bin/docker ps -q)"
test -z "$(/usr/local/bin/docker ps -aq --filter label=leon.test=ubuntu-multiarch)"
test -z "$(/usr/local/bin/docker network ls -q --filter label=leon.test=ubuntu-multiarch)"
sha256sum -c "$work/hooks-config.sha256"
for iface in wl0 wl1 wl2 wl3; do
  printf 'WIRELESS %s isup=' "$iface"
  /usr/sbin/wl -i "$iface" isup
done
printf 'LOADED_MODULES='
wc -l < /proc/modules
if grep -q '^br_netfilter ' /proc/modules; then exit 93; fi
cat /proc/cgroups
printf 'VPN_SERVER1_STATE=%s\n' "$(nvram get vpn_server1_state)"
printf 'VPN_SERVER1_ERRNO=%s\n' "$(nvram get vpn_server1_errno)"
/bin/fc status
state=$(bcm_bootstate)
printf '%s\n' "$state" | grep -q 'Booted Partition: First'
printf '%s\n' "$state" | grep -q 'Reboot Partition: Second'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
echo UBUNTU_MULTIARCH_FINAL_UNCOMMITTED_STATE_PASS
