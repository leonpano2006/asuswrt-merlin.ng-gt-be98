#!/usr/bin/bash
set -eu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
systemctl --version
test "$(nvram get productid)" = GT-BE98
case "$(uname -v)" in '#36 '*) ;; *) exit 91;; esac
grep -q 'root=/dev/ubiblock0_4' /proc/cmdline
test "$(readlink /proc/1/exe)" = /usr/lib/systemd/systemd
test ! -L /run
test "$(readlink /var/run)" = /run
test -S /run/systemd/private
state=$(bcm_bootstate)
printf '%s\n' "$state"
printf '%s\n' "$state" | grep -q 'Reboot Partition: Second'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
systemctl --no-pager show asus-rc.service -p ActiveState -p SubState -p MainPID -p Result -p ControlGroup -p Delegate
test "$(systemctl is-active asus-rc.service)" = active
test "$(systemctl is-active leon-local-ready.service)" = active
leon-rcctl ping
broker=$(systemctl show asus-rc.service -p MainPID --value)
test "$broker" -gt 1
manager=''
for status in /proc/[0-9]*/status; do
 [ "$(awk '$1=="PPid:"{print $2}' "$status" 2>/dev/null || true)" = "$broker" ] || continue
 pid=${status#/proc/}; pid=${pid%/status}
 if [ "$(readlink /proc/$pid/exe)" = /usr/sbin/rc ]; then manager=$pid; fi
done
test -n "$manager"
grep -q leon-trial-bootguard /proc/$manager/maps
for service in httpd dropbear watchdog wdtd; do
 pids=$(pidof "$service"); test -n "$pids"
 for pid in $pids; do
  printf 'SERVICE %s pid=%s exe=%s\n' "$service" "$pid" "$(readlink /proc/$pid/exe)"
  if grep -q leon-trial-bootguard /proc/$pid/maps; then exit 92; fi
 done
done
for iface in wl0 wl1 wl2 wl3; do
 test -d /sys/class/net/$iface
 test "$(/usr/sbin/wl -i "$iface" isup)" = 1
done
for module in pktrunner rdpa dhd rtl8372 btrfs; do
 awk -v m="$module" '$1==m{ok=1}END{exit !ok}' /proc/modules
done
test "$(cat /proc/sys/kernel/tainted)" = 4097
/bin/fc status | grep 'HW Acceleration <Enabled>'
/bin/fc status | grep 'Acceleration Mode: <L2 & L3>'
for controller in memory pids cpuacct devices freezer; do
 test -d /sys/fs/cgroup/$controller
done
awk '$2=="/usr/local" && $3=="btrfs"{ok=1}END{exit !ok}' /proc/mounts
awk '$2=="/jffs" && $3=="btrfs"{ok=1}END{exit !ok}' /proc/mounts
cat /sys/class/watchdog/watchdog0/identity /sys/class/watchdog/watchdog0/timeout
printf 'ASUS_RC_MANAGER_PID=%s\n' "$manager"
uname -a
cat /proc/uptime
systemctl --failed --no-pager
journalctl --sync
test "$(nvram get vpn_server1_state)" = 2
test "$(nvram get vpn_server1_errno)" = 0
test -d /sys/class/net/tun21
test -n "$(pidof vpnserver1)"
printf 'SYSTEMD_PHYSICAL_BASELINE_PASS\n'
