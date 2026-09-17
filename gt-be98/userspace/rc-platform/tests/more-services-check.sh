#!/bin/busybox sh
set -eu
trap 'status=$?; if [ "$status" -ne 0 ]; then journalctl --no-pager -o cat -u asus-rc.service -u asus-crond.service -u asus-infosvr.service -u asus-cron-cleanup.service; fi' EXIT
mkdir -p /run/systemd/system/asus-rc.service.d /run/systemd/system/asus-infosvr.service.d
cat > /run/systemd/system/asus-rc.service.d/90-services-lab.conf <<'EOF'
[Unit]
FailureAction=none
[Service]
ExecStart=
ExecStart=/usr/libexec/leon-rc-broker --test-power /usr/libexec/services-probe
EOF
# Only discovery is mocked: QEMU has no Broadcom NVRAM and no LAN hardware.
# The cron daemon, production units and rc entry points are real.
cat > /run/systemd/system/asus-infosvr.service.d/90-services-lab.conf <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/libexec/infosvr-mock br0
EOF
systemctl daemon-reload
if ! systemctl start asus-rc.service; then
    journalctl --no-pager -o cat -u asus-rc.service -u asus-crond.service -u asus-infosvr.service
    exit 1
fi
systemctl is-active --quiet asus-crond.service asus-infosvr.service
systemctl stop asus-rc.service
# systemctl waits for the named stop job, not every propagated PartOf job.
# The cleanup is ordered after that manager job; wait for its own completion.
i=0
until test "$(systemctl show asus-cron-cleanup.service -p ActiveState --value)" = inactive; do
    i=$((i+1)); test "$i" -lt 28; sleep 1
done
# An empty cgroup excludes zombies; PID 1 may finish reaping just afterward.
i=0
while test -d /proc/"$(cat /run/cron-child-pid)"; do
    i=$((i+1)); test "$i" -lt 6; sleep 1
done
test "$(systemctl show asus-cron-cleanup.service -p Result --value)" = success
test "$(cat /run/cron-child-terminated)" = terminated
echo LAB_MORE_SERVICES_CRON_JOB_SHUTDOWN_DRAIN_PASS
for u in crond infosvr; do
    test "$(systemctl show asus-$u.service -p ActiveState --value)" = inactive
    ! /bin/busybox pidof "$u"
done
journalctl --sync
journalctl --no-pager -o cat -u asus-rc.service > /run/more-services-journal
for name in LEGACY_FORK PRE_READY_AND_CRON_JOB_PRESERVED RECOVERY_STOP FAILURE_NO_FALLBACK DUPLICATE_OWNER READY DRAIN; do
    grep -qx "LAB_MORE_SERVICES_${name}_PASS" /run/more-services-journal
    echo "LAB_MORE_SERVICES_${name}_PASS"
done
echo LAB_MORE_SERVICES_PARTOF_STOP_PASS
rm /run/systemd/system/asus-rc.service.d/90-services-lab.conf /run/systemd/system/asus-infosvr.service.d/90-services-lab.conf
rmdir /run/systemd/system/asus-rc.service.d /run/systemd/system/asus-infosvr.service.d
systemctl daemon-reload
systemctl reset-failed
echo LAB_MORE_SERVICES_ALL_PASS
