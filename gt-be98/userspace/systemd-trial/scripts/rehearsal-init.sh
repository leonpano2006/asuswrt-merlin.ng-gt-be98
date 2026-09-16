#!/bin/busybox sh
set -eu
export PATH=/bin
/bin/busybox --install -s /bin
exec </dev/console >/dev/console 2>&1
echo QEMU_LAB_INIT_REACHED
trap 'echo LAB_SYSTEMD_EARLY_FAILURE; poweroff -f; while :; do sleep 1; done' EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
losetup -r /dev/loop0 /rootfs.squashfs
mount -t squashfs -o ro /dev/loop0 /newroot
mount -t devtmpfs devtmpfs /newroot/dev
trap - EXIT
exec switch_root /newroot /sbin/init
