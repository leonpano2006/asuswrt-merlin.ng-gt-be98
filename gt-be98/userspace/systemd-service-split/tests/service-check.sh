#!/bin/busybox sh
set -eu
# Only the offline rehearsal adds this script. Use the actual production unit
# and ordering graph, substituting the Broadcom-dependent rc backend in RAM.
mkdir -p /run/systemd/system/asus-rc.service.d
cat > /run/systemd/system/asus-rc.service.d/90-service-lab.conf <<'EOF'
[Unit]
FailureAction=none
[Service]
ExecStart=
ExecStart=/usr/libexec/leon-rc-broker --test-power /usr/libexec/service-probe
EOF
systemctl daemon-reload
if ! systemctl start asus-rc.service; then
    journalctl --no-pager -o cat -u asus-rc.service -u asus-haveged.service
    exit 1
fi
systemctl is-active --quiet asus-haveged.service
pid=$(systemctl show asus-haveged.service -p MainPID --value)
test "$pid" -gt 1
systemctl stop asus-rc.service
test "$(systemctl show asus-haveged.service -p ActiveState --value)" = inactive
test ! -d /proc/"$pid"
! /bin/busybox pidof haveged
journalctl --sync
journalctl --no-pager -o cat -u asus-rc.service > /run/service-split-journal
for name in LEGACY_AND_FORK_BOUNDARY BEFORE_READY_SINGLE_OWNER RECOVERY_AND_EXPLICIT_STOP FAILURE_NO_LEGACY_FALLBACK DUPLICATE_OWNER_REJECTED MANAGER_READY MANAGER_DRAIN; do
    grep -qx "LAB_SERVICE_${name}_PASS" /run/service-split-journal
    echo "LAB_SERVICE_${name}_PASS"
done
echo LAB_SERVICE_PARTOF_STOP_PASS
rm /run/systemd/system/asus-rc.service.d/90-service-lab.conf
rmdir /run/systemd/system/asus-rc.service.d
systemctl daemon-reload
# The manager may have garbage-collected the now inactive units already.
# Clear the intentional failures from this isolated regression suite.
systemctl reset-failed
echo LAB_SERVICE_SPLIT_ALL_PASS
