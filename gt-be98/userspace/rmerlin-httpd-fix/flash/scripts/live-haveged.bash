#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
test "$(systemctl is-active asus-haveged.service)" = active
pid=$(systemctl show asus-haveged.service -p MainPID --value)
test "$pid" -gt 1
test "$(pidof haveged)" = "$pid"
test "$(readlink /proc/$pid/exe)" = /usr/sbin/haveged
grep -q '/asus-haveged.service' /proc/$pid/cgroup
systemctl show asus-haveged.service -p ActiveState -p SubState -p MainPID -p Result -p NRestarts -p ControlGroup
test "$(systemctl --failed --no-legend --no-pager | wc -l)" = 0
echo HAVEGED_SINGLE_SYSTEMD_OWNER_PASS
