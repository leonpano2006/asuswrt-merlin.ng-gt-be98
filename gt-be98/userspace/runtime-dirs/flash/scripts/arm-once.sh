#!/bin/sh
set -eu
case "$(uname -v)" in '#35 '*) ;; *) exit 91;; esac
grep -q 'root=/dev/ubiblock0_6' /proc/cmdline
state=$(bcm_bootstate)
printf '%s\n' "$state" | grep -q 'Booted Partition: Second'
printf '%s\n' "$state" | grep -q 'committed 2 valid 1,2 seq 47,46'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
test "$(head -c 75788288 /dev/ubi0_4 | sha256sum | cut -d ' ' -f 1)" = af038997f690e9378941810a6323f681de521cf23a85199d2f832dfbe57176f2
bcm_bootstate 6
state=$(bcm_bootstate)
printf '%s\n' "$state"
printf '%s\n' "$state" | grep -q BOOT_SET_PART1_IMAGE_ONCE
printf '%s\n' "$state" | grep -q 'committed 2 valid 1,2 seq 47,46'
date -u
sync
echo USRMERGE_SLOT1_ONCE_ARMED
/sbin/reboot
