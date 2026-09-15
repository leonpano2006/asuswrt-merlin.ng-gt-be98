#!/bin/sh
set -eu
export PATH=/sbin:/bin:/usr/sbin:/usr/bin
case "$(uname -v)" in '#35 '*) ;; *) exit 91;; esac
grep -q 'root=/dev/ubiblock0_6' /proc/cmdline
test "$(cat /sys/class/ubi/ubi0_3/reserved_ebs)" = 107
test "$(cat /sys/class/ubi/ubi0_4/reserved_ebs)" = 606
boot=$(sha256sum /dev/ubi0_3 | cut -d ' ' -f 1)
root=$(head -c 75804672 /dev/ubi0_4 | sha256sum | cut -d ' ' -f 1)
fallback_boot=$(sha256sum /dev/ubi0_5 | cut -d ' ' -f 1)
fallback_root=$(sha256sum /dev/ubi0_6 | cut -d ' ' -f 1)
loader=$(sha256sum /dev/mtd1 | cut -d ' ' -f 1)
printf 'NEW_BOOTFS=%s\nNEW_ROOTFS=%s\nFALLBACK_BOOTFS=%s\nFALLBACK_ROOTFS=%s\nLOADER=%s\n' "$boot" "$root" "$fallback_boot" "$fallback_root" "$loader"
test "$boot" = 2a7c327db1a185d17ba5f7b72097abf6b6158e6f2810ed7a26873144a4a8f10f
test "$root" = 9d13b0b5789843e691cf08f2083c189dbc61f48eeb5d433795183e455b4aa026
test "$fallback_boot" = 61403034cd7f49f25210f7e6154e421a784519b36874b618a34c0e2c3a25c291
test "$fallback_root" = f6dd764de8cd5b0a5724193f771b180950c0c716f8120b9095bf54cda5cf2347
test "$loader" = 5721efb444680b250a40295fdad605f303749a0140468eba1f0f695f268517c3
state=$(bcm_bootstate)
printf '%s\n' "$state"
printf '%s\n' "$state" | grep -q 'Booted Partition: Second'
printf '%s\n' "$state" | grep -Eq 'First +partition commit flag +: 0'
printf '%s\n' "$state" | grep -Eq 'Second +partition commit flag +: 1'
echo VERIFIED_NEW_IMAGE_FALLBACK_AND_LOADER
cat /sys/class/ubi/ubi0/avail_eraseblocks
