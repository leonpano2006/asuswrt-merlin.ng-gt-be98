#!/bin/busybox sh
set -eu
export PATH=/usr/bin:/usr/sbin:/bin:/sbin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
mkdir -p /run/asus-test-nvram
rm -f /run/rc-probe-drained /run/rc-probe-state /run/rc-probe-notifications
for abi in aarch64 armel armhf; do /usr/libexec/abi-probe-$abi; done
/usr/libexec/notify-probe --missing
mv /etc/ld.so.preload /etc/ld.so.preload.test-held
if systemctl start asus-rc-lab.service; then exit 1; fi
test "$(systemctl show asus-rc-lab.service -p ExecMainStatus --value)" = 10
mv /etc/ld.so.preload.test-held /etc/ld.so.preload
systemctl reset-failed asus-rc-lab.service
echo LAB_RC_MISSING_PRELOAD_REJECTED_PASS
systemctl start asus-rc-lab.service
test "$(systemctl is-active asus-rc-lab.service)" = active
broker=$(systemctl show asus-rc-lab.service -p MainPID --value)
test "$broker" -gt 1
test "$(cat /run/rc-probe-pid)" -gt 1
test "$broker" != "$(cat /run/rc-probe-pid)"
leon-rcctl ping
/usr/libexec/notify-probe
test "$(cat /run/rc-probe-notifications)" = 7
leon-rcctl start
i=0; until test "$(cat /run/rc-probe-state 2>/dev/null || true)" = 12; do i=$((i+1)); test "$i" -lt 10; sleep 1; done
leon-rcctl stop
i=0; until test "$(cat /run/rc-probe-state)" = 2; do i=$((i+1)); test "$i" -lt 10; sleep 1; done
leon-rcctl restart
i=0; until test "$(cat /run/rc-probe-state)" = 1; do i=$((i+1)); test "$i" -lt 10; sleep 1; done
echo LAB_RC_START_STOP_RESTART_ROUTING_PASS
/usr/libexec/static-probe
test "$(cat /run/leon-rc/power-request)" = reboot
test ! -e /run/rc-probe-drained
test "$(readlink /proc/1/exe)" = /usr/lib/systemd/systemd
echo LAB_RC_REBOOT_REQUEST_NO_EARLY_DRAIN_PASS
systemctl stop asus-rc-lab.service
test "$(cat /run/rc-probe-drained)" = 15
test "$(systemctl show asus-rc-lab.service -p Result --value)" = success
test ! -S /run/leon-rc/control
/usr/libexec/notify-probe --missing
rm /run/rc-probe-drained
systemctl start asus-rc-lab.service
systemctl stop asus-rc-lab.service
test "$(cat /run/rc-probe-drained)" = 3
test "$(systemctl show asus-rc-lab.service -p Result --value)" = success
journalctl --sync
journalctl --no-pager -o cat -u asus-rc-lab.service > /run/rc-lab-journal
grep -q LAB_RC_IDENTITY_GUARD_SUBREAPER_MOUNTS_PASS /run/rc-lab-journal
grep -q LAB_RC_ORDERED_DRAIN_PASS /run/rc-lab-journal
grep -q LAB_RC_EARLY_NOTIFICATION_QUEUED_PASS /run/rc-lab-journal
grep -q LAB_RC_BSP_SIGNAL_MASK_PASS /run/rc-lab-journal
echo LAB_RC_EARLY_NOTIFICATION_QUEUED_PASS
echo LAB_RC_BSP_SIGNAL_MASK_PASS
echo LAB_RC_IDENTITY_GUARD_SUBREAPER_MOUNTS_PASS
echo LAB_RC_ORDERED_DRAIN_PASS
systemctl start asus-rc-lab.service
kill -KILL "$(cat /run/rc-probe-pid)"
i=0; until test "$(systemctl show asus-rc-lab.service -p ActiveState --value)" = failed; do i=$((i+1)); test "$i" -lt 15; sleep 1; done
test "$(systemctl show asus-rc-lab.service -p NRestarts --value)" = 0
/usr/libexec/notify-probe --missing
test "$(readlink /proc/1/exe)" = /usr/lib/systemd/systemd
echo LAB_RC_CHILD_FAILURE_ISOLATED_PASS
LD_TRACE_LOADED_OBJECTS=1 LD_WARN=1 LD_BIND_NOW=1 /usr/sbin/rc > /run/rebuilt-rc-linkage 2>&1
cat /run/rebuilt-rc-linkage
if grep -E 'undefined symbol|not found|cannot be preloaded' /run/rebuilt-rc-linkage; then exit 1; fi
echo LAB_RC_REBUILT_BINARY_RELOCATIONS_PASS
/usr/libexec/crypt-probe
set +e
/usr/libexec/ovpn-role-probe /usr/libexec/libovpn-stock.so
stock_status=$?
set -e
test "$stock_status" = 77
/usr/libexec/ovpn-role-probe /usr/lib/arm-linux-gnueabi/libovpn.so
/usr/libexec/ovpn-no-manager-probe /usr/lib/arm-linux-gnueabi/libovpn.so
echo LAB_RC_COMPATIBILITY_ALL_PASS
/usr/libexec/service-check.sh
systemctl start asus-rc-real-power.service
