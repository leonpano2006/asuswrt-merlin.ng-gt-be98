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
test "$(cat /sys/class/ubi/ubi0_4/reserved_ebs)" = 607
test "$(cat /sys/class/ubi/ubi0/eraseblock_size)" = 126976
free=$(cat /sys/class/ubi/ubi0/avail_eraseblocks)
test "$free" -ge 20
test $((free + 107 + 607)) -ge 722
test "$(sha256sum /dev/ubi0_5 | cut -d ' ' -f 1)" = 61403034cd7f49f25210f7e6154e421a784519b36874b618a34c0e2c3a25c291
test "$(sha256sum /dev/ubi0_6 | cut -d ' ' -f 1)" = f6dd764de8cd5b0a5724193f771b180950c0c716f8120b9095bf54cda5cf2347
test "$(sha256sum /dev/mtd1 | cut -d ' ' -f 1)" = 5721efb444680b250a40295fdad605f303749a0140468eba1f0f695f268517c3
test "$(sha256sum /tmp/leon36-a53-runtimes.pkgtb | cut -d ' ' -f 1)" = 7d48c2274be8dae6179096208a738d5214b321805b6d1fa9f0736bf23eff92f9
test "$(wc -c < /tmp/leon36-a53-runtimes.pkgtb)" = 89439308
/bin/fc status | grep 'HW Acceleration <Enabled>'
echo A53_RUNTIME_INACTIVE_SLOT1_FLASH_START
/bin/bcm_flasher /tmp/leon36-a53-runtimes.pkgtb
sync
echo A53_RUNTIME_INACTIVE_SLOT1_FLASH_OK
bcm_bootstate
