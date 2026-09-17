#!/bin/busybox sh
set -eu
trap 'status=$?; if [ "$status" -ne 0 ]; then journalctl --no-pager -o cat -u asus-rc.service -u asus-mdns.service -u asus-ntpd.service; fi' EXIT
mkdir -p /run/systemd/system/asus-rc.service.d
cat > /run/systemd/system/asus-rc.service.d/90-network-lab.conf <<'EOF'
[Unit]
FailureAction=none
[Service]
ExecStart=
ExecStart=/usr/libexec/leon-rc-broker --test-power /usr/libexec/network-services-probe
EOF
# Both production daemons run unmodified; no host NIC or clock is exposed.
# Normal ASUS initialization supplies these accounts; the hardware stub does not.
grep -q '^nobody:' /etc/passwd || printf 'nobody:x:65534:65534:nobody:/:/bin/false\n' >> /etc/passwd
grep -q '^nobody:' /etc/group || printf 'nobody:x:65534:\n' >> /etc/group
ip link set lo up
systemctl daemon-reload
systemctl start asus-rc.service
systemctl is-active --quiet asus-mdns.service asus-ntpd.service
systemctl stop asus-rc.service
for u in mdns ntpd; do
    i=0
    until test "$(systemctl show asus-$u.service -p ActiveState --value)" = inactive; do
        i=$((i+1));test "$i" -lt 15;sleep 1
    done
done
! /bin/busybox pidof avahi-daemon
! /bin/busybox pidof ntp
journalctl --sync
journalctl --no-pager -o cat -u asus-rc.service > /run/network-services-journal
for name in LEGACY_CHILD_ROUTING PRE_READY_CONFIG_CALLBACK RECONFIGURE_RECOVERY_ISOLATION DUPLICATE_AND_ARGUMENT_GUARDS FAILURE_NO_FALLBACK READY DRAIN; do
    grep -qx "LAB_NETWORK_SERVICES_${name}_PASS" /run/network-services-journal
    echo "LAB_NETWORK_SERVICES_${name}_PASS"
done
! grep -q 'Permission denied\|Failed to read /tmp/avahi/services' /run/network-services-journal
journalctl --no-pager -o cat -u asus-mdns.service > /run/mdns-service-journal
! grep -q 'Permission denied\|Failed to read /tmp/avahi/services' /run/mdns-service-journal
echo LAB_NETWORK_SERVICES_PARTOF_STOP_PASS
rm /run/systemd/system/asus-rc.service.d/90-network-lab.conf
rmdir /run/systemd/system/asus-rc.service.d
systemctl daemon-reload
systemctl reset-failed
echo LAB_NETWORK_SERVICES_ALL_PASS
