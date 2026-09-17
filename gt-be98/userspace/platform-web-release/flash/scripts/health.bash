#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
test "$(nvram get productid)" = GT-BE98
test "$(readlink /proc/1/exe)" = /usr/lib/systemd/systemd
grep -q '3006.102.9-beta1-leon10' /usr/share/leon-upstream.json
case "$(uname -v)" in '#36 '*) ;; *) exit 91;; esac
sha256sum /usr/sbin/rc /usr/sbin/httpd /usr/lib/arm-linux-gnueabi/libshared.so /www/aimesh/aimesh_topology.html
test "$(sha256sum /usr/sbin/rc | cut -d' ' -f1)" = cf121058ede3661d8b5a9f3bc3e8aed2850d533205b71ccf20bcf3a46c221981
test "$(sha256sum /usr/sbin/httpd | cut -d' ' -f1)" = 2035aca8e26a14b0823e340ac08e2eddeb13d494d2595bc54e0014d4ba73cd0b
test "$(sha256sum /usr/lib/arm-linux-gnueabi/libshared.so | cut -d' ' -f1)" = 06eb9ca13f4de144c65aad7b5e013b38b5bfa128bc4b8688e474d2c6f3e7a779
test "$(sha256sum /www/aimesh/aimesh_topology.html | cut -d' ' -f1)" = 3cef091a58002ec0b1928473531d8c41355219cc5c1d20f6dc8bc4152f8e7e4c
if awk '$2=="/usr/sbin/httpd" || $2=="/usr/lib/arm-linux-gnueabi/libshared.so" || $2=="/www/aimesh/aimesh_topology.html" {found=1}END{exit !found}' /proc/mounts; then
    echo 'Unexpected RAM replacement of firmware files'; exit 92
fi
for name in rc sshd haveged crond infosvr mdns ntpd syslogd klogd eapd acsd2 wlceventd roamast httpd httpds hotplug2 networkmap cfg-server; do
    unit="asus-$name.service"
    systemctl show "$unit" -p ActiveState -p SubState -p Result -p MainPID -p NRestarts
    test "$(systemctl is-active "$unit")" = active
    # One acsd2 restart was observed during the first radio initialization.
    # Preserve this known issue explicitly; a separate interval check must
    # establish that the count and PID no longer change before RAM acceptance.
    if [ "$name" = acsd2 ]; then
        test "$(systemctl show "$unit" -p NRestarts --value)" = 1
    else
        test "$(systemctl show "$unit" -p NRestarts --value)" = 0
    fi
done
for iface in wl0 wl1 wl2 wl3; do
    test "$(wl -i "$iface" isup)" = 1
    echo "RADIO_UP $iface"
done
/bin/fc status | grep -E 'HW Acceleration|Acceleration Mode'
/bin/fc status | grep -q 'HW Acceleration <Enabled>'
test "$(systemctl --failed --no-legend --no-pager | wc -l)" = 0
awk '$2=="/tmp/mnt/JFFS" && $3=="btrfs"{ok=1}END{exit !ok}' /proc/mounts
test "$(readlink /usr/lib/arm-linux-gnueabihf)" = /tmp/mnt/JFFS/system-libs/gt-be98/8da410f090d92cff/arm-linux-gnueabihf
/lib/ld-linux-armhf.so.3 --version | head -1
systemctl --version
for feature in OPENSSL CURL ZLIB ZSTD BLKID; do systemctl --version | grep -q "+$feature"; done
/usr/sbin/sysctl --version
state=$(bcm_bootstate)
printf '%s\n' "$state"
printf '%s\n' "$state" | grep -q 'Booted Partition: First'
printf '%s\n' "$state" | grep -q 'Reboot Partition: Second'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
date -u
cat /proc/uptime
echo LEON10_PHYSICAL_HEALTH_PASS
