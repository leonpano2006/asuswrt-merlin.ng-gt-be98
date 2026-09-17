#!/bin/sh
set -eu
case "$(uname -v)" in '#35 '*) ;; *) exit 91;; esac
grep -q 'root=/dev/ubiblock0_6' /proc/cmdline
state=$(bcm_bootstate)
printf '%s\n' "$state" | grep -q 'Booted Partition: Second'
printf '%s\n' "$state" | grep -q 'committed 2 valid 1,2 seq 47,46'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
test "$(head -c 78458880 /dev/ubi0_4 | sha256sum | cut -d ' ' -f 1)" = 4200e7ea7e5340ac0407ce18c9a1ae628c9a37d2dbef665e24ae2e566331dd9c
bcm_bootstate 6
state=$(bcm_bootstate)
printf '%s\n' "$state"
printf '%s\n' "$state" | grep -q BOOT_SET_PART1_IMAGE_ONCE
printf '%s\n' "$state" | grep -q 'committed 2 valid 1,2 seq 47,46'
date -u
sync
echo SYSTEMD257_SLOT1_ONCE_ARMED
/sbin/reboot
