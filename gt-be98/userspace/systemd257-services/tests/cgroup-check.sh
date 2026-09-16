#!/bin/busybox sh
set -eux
test "$(systemctl --version | head -n 1)" = 'systemd 257 (257.13-gt-be98)'
for controller in cpuacct memory devices freezer pids; do
    awk -v p="/sys/fs/cgroup/$controller" '$2==p && $3=="cgroup" {ok=1} END{exit !ok}' /proc/mounts
done
awk '$2=="/sys/fs/cgroup/unified" && $3=="cgroup2" {ok=1} END{exit !ok}' /proc/mounts
test -e /sys/fs/cgroup/devices/devices.allow
test -e /sys/fs/cgroup/memory/memory.limit_in_bytes
test -e /sys/fs/cgroup/pids/cgroup.procs
echo LAB_SYSTEMD_257_HYBRID_WITH_V1_CONTROLLERS_PASS
