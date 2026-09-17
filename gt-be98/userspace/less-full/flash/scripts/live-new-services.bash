#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
test "$(systemctl --version | head -1)" = 'systemd 257 (257.13-gt-be98)'
test "$(/usr/bin/less --version | head -1)" = 'less 704 (POSIX regular expressions)'
test ! -L /usr/bin/less
test "$(sha256sum /usr/bin/less | cut -d' ' -f1)" = 855c22d703782371ca11dac723e6ff322e9df9c5cf2a5694edaa376dd5bc4427
if awk '$2=="/usr/bin"{found=1}END{exit !found}' /proc/mounts; then
    echo 'Unexpected live /usr/bin overlay on native-less firmware' >&2
    exit 1
fi
for controller in cpuacct memory devices freezer pids; do
    awk -v p="/sys/fs/cgroup/$controller" '$2==p && $3=="cgroup"{ok=1}END{exit !ok}' /proc/mounts
done
awk '$2=="/sys/fs/cgroup/unified" && $3=="cgroup2"{ok=1}END{exit !ok}' /proc/mounts
for daemon in crond infosvr haveged; do
    unit="asus-$daemon.service"
    test "$(systemctl is-active "$unit")" = active
    pid=$(systemctl show "$unit" -p MainPID --value)
    test "$pid" -gt 1
    test "$(pidof "$daemon")" = "$pid"
    grep -q "/$unit" "/proc/$pid/cgroup"
    systemctl show "$unit" -p ActiveState -p SubState -p MainPID -p Result -p NRestarts -p ControlGroup
done
test "$(systemctl is-active asus-cron-cleanup.service)" = active
test "$(systemctl --failed --no-legend --no-pager | wc -l)" = 0
test "$(sha256sum /usr/sbin/rc | cut -d' ' -f1)" = 5191c8a0bc759add07c915682375b986d89d81574535ab910beddbec24e7b87d
test "$(sha256sum /usr/sbin/httpd | cut -d' ' -f1)" = e1c6013f9e535cd76294a4acc814b5b985fb487e79dff60066b18d52cd8bf450
echo SYSTEMD257_CRON_DISCOVERY_HYBRID_AND_NATIVE_LESS_PASS
