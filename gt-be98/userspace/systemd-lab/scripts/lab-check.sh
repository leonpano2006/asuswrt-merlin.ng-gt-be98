#!/bin/busybox sh
set -eu
set -x
export PATH=/usr/bin:/usr/sbin:/bin:/sbin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
exec >/dev/console 2>&1
trap 'echo LAB_SYSTEMD_CHECK_FAILURE; /bin/busybox poweroff -f' EXIT
test "$(readlink /proc/1/exe)" = /usr/lib/systemd/systemd
test -d /run/systemd/system
test -S /run/systemd/private
echo LAB_SYSTEMD_PID1_PASS
test -d /run && test ! -L /run
test "$(readlink /var/run)" = /run
awk '$2 == "/run" && $3 == "tmpfs" {ok=1} END {exit !ok}' /proc/mounts
echo LAB_SYSTEMD_RUN_LAYOUT_PASS
systemctl start leon-guard.service
test "$(systemctl show leon-guard.service -p ExecMainStatus --value)" = 0
systemctl stop leon-guard.service
echo LAB_SYSTEMD_TRIAL_GUARD_BOUNDARY_PASS
systemctl start leon-worker.service
first=$(systemctl show leon-worker.service -p MainPID --value)
test "$first" -gt 1
test "$(systemctl is-active leon-worker.service)" = active
systemctl restart leon-worker.service
second=$(systemctl show leon-worker.service -p MainPID --value)
test "$second" -gt 1 && test "$first" != "$second"
echo LAB_SYSTEMD_SERVICE_RESTART_PASS
cg=$(systemctl show leon-worker.service -p ControlGroup --value)
test -n "$cg"
for controller in memory pids; do
    test -d "/sys/fs/cgroup/$controller$cg"
done
test "$(cat /sys/fs/cgroup/memory$cg/memory.limit_in_bytes)" = 67108864
test "$(cat /sys/fs/cgroup/pids$cg/pids.max)" = 16
test "$(systemctl show leon-worker.service -p Delegate --value)" = yes
echo LAB_SYSTEMD_V1_MEMORY_PIDS_DELEGATION_PASS
systemctl kill --kill-whom=main --signal=KILL leon-worker.service
i=0
while :; do
    third=$(systemctl show leon-worker.service -p MainPID --value)
    if [ "$third" -gt 1 ] && [ "$third" != "$second" ]; then break; fi
    i=$((i + 1)); test "$i" -lt 30
    sleep 1
done
test "$(systemctl show leon-worker.service -p NRestarts --value)" -ge 1
echo LAB_SYSTEMD_SERVICE_RECOVERY_PASS
systemctl stop leon-worker.service
test "$(systemctl show leon-worker.service -p ActiveState --value)" = inactive
test ! -d /proc/$third
echo LAB_SYSTEMD_SERVICE_STOP_PASS
journalctl --sync
journalctl --no-pager -o cat -u leon-worker.service > /run/leon-worker-journal.txt
grep -q LEON_WORKER_STARTED /run/leon-worker-journal.txt
echo LAB_SYSTEMD_JOURNAL_PASS
systemctl daemon-reexec
i=0
until systemctl show --property=Version --value; do
    i=$((i + 1)); test "$i" -lt 30; sleep 1
done
test "$(readlink /proc/1/exe)" = /usr/lib/systemd/systemd
echo LAB_SYSTEMD_REEXEC_PASS
echo LAB_SYSTEMD_CONFIGURATION_MOUNTS
awk '$5 ~ /^\/(tmp|etc)/ {print}' /proc/self/mountinfo
for pid in 1 $(systemctl show systemd-journald.service -p MainPID --value); do
    for fd in /proc/$pid/fd/* /proc/$pid/cwd; do
        target=$(readlink "$fd" || true)
        case "$target" in /tmp/*|/etc/*) echo "$fd -> $target";; esac
    done
done
echo LAB_SYSTEMD_ALL_PASS
trap - EXIT
systemctl --no-block poweroff
