#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
systemctl --version
cat /usr/share/leon-upstream.json
cat /proc/uptime /proc/sys/kernel/tainted
systemctl --failed --no-pager
for unit in asus-sshd.service asus-rc.service asus-haveged.service asus-crond.service asus-infosvr.service asus-mdns.service asus-ntpd.service; do
    test "$(systemctl is-active "$unit")" = active
    systemctl show "$unit" -p ActiveState -p Result -p NRestarts
    test "$(systemctl show "$unit" -p NRestarts --value)" = 0
done
test "$(systemctl --failed --no-legend --no-pager | wc -l)" = 0
stat -c 'RAM_ACCEPT uid=%u mode=%a' /run/leon-systemd-trial/accepted
/bin/fc status | grep -E 'HW Acceleration|Acceleration Mode'
/usr/local/bin/docker info --format 'Docker={{.ServerVersion}} driver={{.Driver}} cgroup={{.CgroupVersion}}'
test -z "$(/usr/local/bin/docker ps -q)"
bcm_bootstate
systemctl show -p UserspaceTimestampMonotonic -p FinishTimestampMonotonic
