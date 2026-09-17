#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
for pair in 'asus-mdns.service avahi-daemon' 'asus-ntpd.service ntp'; do
 read -r unit name <<< "$pair"
 systemctl show "$unit" -p ActiveState -p SubState -p MainPID -p Result -p NRestarts -p ControlGroup
 pids=$(pidof "$name" || true)
 if [ -n "$pids" ]; then
  test "$(systemctl is-active "$unit")" = active
  main=$(systemctl show "$unit" -p MainPID --value)
  test "$main" -gt 1
  grep -q "/$unit" /proc/$main/cgroup
  for pid in $pids; do grep -q "/$unit" /proc/$pid/cgroup; done
 fi
 test "$(systemctl show "$unit" -p Result --value)" = success
done
for key in sw_mode ntp_ready ntp_server0 ntp_server1 ntpd_enable mdns_enable; do printf '%s=' "$key"; nvram get "$key"; done
journalctl -b -u asus-mdns.service -u asus-ntpd.service --no-pager -n 35
systemctl --failed --no-pager
/bin/fc status | grep -E 'HW Acceleration|Acceleration Mode'
echo LIVE_MDNS_NTP_POLICY_AND_OWNERSHIP_PASS
