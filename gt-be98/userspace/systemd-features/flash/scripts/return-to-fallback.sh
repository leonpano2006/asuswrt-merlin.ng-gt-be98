#!/bin/sh
set -eu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
test "$(nvram get productid)" = GT-BE98
test "$(readlink /proc/1/exe)" = /usr/lib/systemd/systemd
case "$(uname -v)" in '#36 '*) ;; *) exit 91;; esac
grep -q 'root=/dev/ubiblock0_4' /proc/cmdline
state=$(bcm_bootstate)
printf '%s\n' "$state" | grep -q 'Booted Partition: First'
printf '%s\n' "$state" | grep -q 'Reboot Partition: Second'
printf '%s\n' "$state" | grep -q 'committed 2 valid 1,2 seq 47,46'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
test "$(head -c 78458880 /dev/ubi0_4 | sha256sum | cut -d ' ' -f 1)" = 4200e7ea7e5340ac0407ce18c9a1ae628c9a37d2dbef665e24ae2e566331dd9c
test "$(sha256sum /dev/ubi0_5 | cut -d ' ' -f 1)" = 61403034cd7f49f25210f7e6154e421a784519b36874b618a34c0e2c3a25c291
test "$(sha256sum /dev/ubi0_6 | cut -d ' ' -f 1)" = f6dd764de8cd5b0a5724193f771b180950c0c716f8120b9095bf54cda5cf2347
test -z "$(/usr/local/bin/docker ps -q)"
/usr/local/sbin/docker-stop
sync
echo SYSTEMD_TRIAL_RETURN_TO_COMMITTED_SLOT2
/usr/bin/systemctl --no-block reboot
