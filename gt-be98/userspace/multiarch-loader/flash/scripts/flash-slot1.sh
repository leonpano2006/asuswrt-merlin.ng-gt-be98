#!/bin/sh
set -eu
export PATH=/sbin:/bin:/usr/sbin:/usr/bin
test "$(nvram get productid)" = GT-BE98
case "$(uname -v)" in '#35 '*) ;; *) exit 91;; esac
grep -q 'root=/dev/ubiblock0_6' /proc/cmdline
state=$(bcm_bootstate)
printf '%s\n' "$state"
printf '%s\n' "$state" | grep -q 'Booted Partition: Second'
printf '%s\n' "$state" | grep -q 'Reboot Partition: Second'
printf '%s\n' "$state" | grep -q 'committed 2 valid 1,2 seq 47,46'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
test "$(cat /sys/class/ubi/ubi0_3/name)" = bootfs1
test "$(cat /sys/class/ubi/ubi0_4/name)" = rootfs1
test "$(cat /sys/class/ubi/ubi0_3/reserved_ebs)" = 107
test "$(cat /sys/class/ubi/ubi0_4/reserved_ebs)" = 606
test "$(cat /sys/class/ubi/ubi0/eraseblock_size)" = 126976
free=$(cat /sys/class/ubi/ubi0/avail_eraseblocks)
test "$free" -ge 21
test $((free + 107 + 606)) -ge 714
test "$(sha256sum /dev/ubi0_5 | cut -d ' ' -f 1)" = 61403034cd7f49f25210f7e6154e421a784519b36874b618a34c0e2c3a25c291
test "$(sha256sum /dev/ubi0_6 | cut -d ' ' -f 1)" = f6dd764de8cd5b0a5724193f771b180950c0c716f8120b9095bf54cda5cf2347
test "$(sha256sum /dev/mtd1 | cut -d ' ' -f 1)" = 5721efb444680b250a40295fdad605f303749a0140468eba1f0f695f268517c3
test "$(sha256sum /tmp/leon36-ubuntu-multiarch.pkgtb | cut -d ' ' -f 1)" = 67f896ed532531a345805dc14303b23b203d4545fb8cb11a5ab5df12d8c7a23d
test "$(wc -c < /tmp/leon36-ubuntu-multiarch.pkgtb)" = 88333388
/bin/fc status | grep 'HW Acceleration <Enabled>'
echo UBUNTU_MULTIARCH_INACTIVE_SLOT1_FLASH_START
/bin/bcm_flasher /tmp/leon36-ubuntu-multiarch.pkgtb
sync
echo UBUNTU_MULTIARCH_INACTIVE_SLOT1_FLASH_OK
bcm_bootstate
