#!/bin/sh
set -eu
case "$(uname -v)" in '#35 '*) ;; *) exit 91;; esac
grep -q 'root=/dev/ubiblock0_6' /proc/cmdline
state=$(bcm_bootstate)
printf '%s\n' "$state" | grep -q 'Booted Partition: Second'
printf '%s\n' "$state" | grep -q 'committed 2 valid 1,2 seq 47,46'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
test "$(head -c 78282752 /dev/ubi0_4 | sha256sum | cut -d ' ' -f 1)" = 8df7322e87b846470bb6d3306f8ac78ab37ecaae63257cfb54c0b500ce22dc9b
bcm_bootstate 6
state=$(bcm_bootstate)
printf '%s\n' "$state"
printf '%s\n' "$state" | grep -q BOOT_SET_PART1_IMAGE_ONCE
printf '%s\n' "$state" | grep -q 'committed 2 valid 1,2 seq 47,46'
date -u
sync
echo SYSTEMD257_SLOT1_ONCE_ARMED
/sbin/reboot
