#!/usr/bin/bash
set -eu
date -u
uname -a
cat /proc/uptime
test "$(nvram get productid)" = GT-BE98
case "$(uname -v)" in '#36 '*) ;; *) exit 91;; esac
grep -q 'root=/dev/ubiblock0_4' /proc/cmdline
test "$(readlink /proc/1/exe)" = /usr/sbin/rc
for name in bin sbin lib; do
    test "$(readlink /$name)" = "usr/$name"
done
test "$(readlink /run)" = var/run
test "$(stat -Lc '%d:%i' /run)" = "$(stat -Lc '%d:%i' /var/run)"
test "$(stat -Lc '%u:%g:%a' /run)" = 0:0:755
test -d /media && test -d /srv
ls -ld /bin /sbin /lib /run /media /srv
state=$(bcm_bootstate)
printf '%s\n' "$state"
printf '%s\n' "$state" | grep -q 'Booted Partition: First'
printf '%s\n' "$state" | grep -q 'Reboot Partition: Second'
printf '%s\n' "$state" | grep -q 'committed 2 valid 1,2 seq 47,46'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
test "$(head -c 75915264 /dev/ubi0_4 | sha256sum | cut -d ' ' -f 1)" = 4f2a9673173a0c32b85a2b1256eaafab4ca96312f134df86e38ae1a58595a88e
test "$(sha256sum /dev/ubi0_5 | cut -d ' ' -f 1)" = 61403034cd7f49f25210f7e6154e421a784519b36874b618a34c0e2c3a25c291
test "$(sha256sum /dev/ubi0_6 | cut -d ' ' -f 1)" = f6dd764de8cd5b0a5724193f771b180950c0c716f8120b9095bf54cda5cf2347
test "$(sha256sum /dev/mtd1 | cut -d ' ' -f 1)" = 5721efb444680b250a40295fdad605f303749a0140468eba1f0f695f268517c3
grep -q leon-trial-bootguard /proc/1/maps
for service in httpd dropbear watchdog; do
    pids=$(pidof "$service")
    test -n "$pids"
    for pid in $pids; do
        printf 'SERVICE %s pid=%s exe=%s\n' "$service" "$pid" "$(readlink "/proc/$pid/exe")"
        if grep -q leon-trial-bootguard "/proc/$pid/maps"; then exit 92; fi
    done
done
for iface in wl0 wl1 wl2 wl3; do
    test -d "/sys/class/net/$iface"
    printf 'WIRELESS %s isup=' "$iface"
    /usr/sbin/wl -i "$iface" isup
done
for module in pktrunner rdpa dhd rtl8372 btrfs; do
    awk -v m="$module" '$1==m{ok=1}END{exit !ok}' /proc/modules
done
awk '$1=="memory" && $4==1{ok=1}END{exit !ok}' /proc/cgroups
test "$(cat /proc/sys/kernel/tainted)" = 4097
/bin/fc status
/bin/fc status | grep -q 'HW Acceleration <Enabled>'
/bin/fc status | grep -q 'Acceleration Mode: <L2 & L3>'
cat /proc/pktrunner/accel0/stats
echo UBUNTU_MULTIARCH_LIVE_PATHS_SERVICES_KERNEL_FALLBACK_PASS
