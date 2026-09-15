#!/bin/busybox sh
set -eu
export PATH=/bin
/bin/busybox --install -s /bin
exec </dev/console >/dev/console 2>&1
echo QEMU_LAB_INIT_REACHED
trap 'echo USRMERGE_GUEST_FAILED; poweroff -f; while :; do sleep 1; done' EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
losetup -r /dev/loop0 /rootfs.squashfs
mount -t squashfs -o ro /dev/loop0 /newroot
mount -t devtmpfs devtmpfs /newroot/dev
mount -t proc proc /newroot/proc
mount -t sysfs sysfs /newroot/sys
mount -t tmpfs tmpfs /newroot/tmp
mkdir -p /newroot/tmp/etc
# Match ASUS rc/init.c: expose each ROM configuration entry as an /etc symlink.
for entry in /newroot/rom/etc/*; do
    name=${entry##*/}
    ln -s /rom/etc/$name /newroot/tmp/etc/$name
done
# Exercise the actual loader cache and all three ABI configuration fragments.
chroot /newroot /usr/sbin/ldconfig
cp /library-probe /newroot/tmp/library-probe
chroot /newroot /tmp/library-probe
cp /userspace-smoke.sh /newroot/tmp/userspace-smoke.sh
touch /newroot/tmp/QEMU_LAB_GUEST
chroot /newroot /bin/busybox sh /tmp/userspace-smoke.sh
for abi in aarch64 armel armhf; do
    cp /abi-probe-$abi /newroot/tmp/abi-probe-$abi
    echo "LAB_ABI_BEGIN $abi"
    chroot /newroot /tmp/abi-probe-$abi
done
count=0
failed=0
while read -r loader program; do
    count=$((count + 1))
    if ! chroot /newroot "$loader" --list "$program" > /tmp/linker.out 2>&1; then
        echo "LAB_LINKER_FAILURE $program"
        cat /tmp/linker.out
        failed=$((failed + 1))
    fi
done < /dynamic-executables.txt
echo "LAB_LINKER_SUMMARY count=$count failed=$failed"
test "$failed" = 0
# Check the genuine ASUS identity function with the new canonical executable path.
mount --bind /identity-probe /newroot/usr/sbin/rc
chroot /newroot /sbin/rc
LD_PRELOAD=/usr/lib/leon-trial-bootguard.so chroot /newroot /sbin/rc
umount /newroot/usr/sbin/rc
echo LAB_USRMERGE_IDENTITY_PASS
# All module bytes are preserved; exercise the module path through /lib and /usr/lib.
chroot /newroot /bin/busybox insmod /lib/modules/4.19.294/kernel/lib/raid6/raid6_pq.ko
chroot /newroot /bin/busybox insmod /usr/lib/modules/4.19.294/kernel/crypto/xor.ko
chroot /newroot /bin/busybox insmod /lib/modules/4.19.294/kernel/fs/btrfs/btrfs.ko
grep -q '^btrfs ' /proc/modules
echo LAB_USRMERGE_MODULE_PATHS_PASS
# Finish by exercising the unchanged trial init and metadata guard as PID 1.
mount --bind /guardcheck /newroot/usr/sbin/rc
cp /provider.so /newroot/tmp/bootguard-provider.so
export LD_LIBRARY_PATH=/tmp
export PATH=/sbin:/usr/sbin:/bin:/usr/bin
trap - EXIT
exec chroot /newroot /sbin/init
