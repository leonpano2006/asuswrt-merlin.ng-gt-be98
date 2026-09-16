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
mkdir -p /newroot/dev/pts /newroot/dev/shm
mount -t devpts devpts /newroot/dev/pts
mount -t tmpfs -o mode=1777 tmpfs /newroot/dev/shm
mount -t proc proc /newroot/proc
mount -t sysfs sysfs /newroot/sys
mount -t tmpfs -o mode=1777 tmpfs /newroot/tmp
mount -t tmpfs -o mode=0755 tmpfs /newroot/run
mount -t tmpfs -o mode=0755 tmpfs /newroot/var
mkdir -p /newroot/tmp/etc /newroot/var/lib /newroot/var/log /newroot/var/cache
ln -s /run /newroot/var/run
ln -s /run/lock /newroot/var/lock
mkdir -p /newroot/run/lock
for entry in /newroot/rom/etc/*; do
    name=${entry##*/}
    ln -s /rom/etc/$name /newroot/tmp/etc/$name
done
for name in systemd passwd group machine-id os-release fstab mtab; do
    rm -f /newroot/tmp/etc/$name
done
mkdir -p /newroot/tmp/etc/systemd
cat > /newroot/tmp/etc/passwd <<'EOF'
root:x:0:0:root:/root:/bin/sh
nobody:x:65534:65534:nobody:/:/bin/false
EOF
cat > /newroot/tmp/etc/group <<'EOF'
root:x:0:
systemd-journal:x:190:
nogroup:x:65534:
EOF
printf 'b71c4c2e09ab4c88ae609ebfb9372301\n' > /newroot/tmp/etc/machine-id
printf 'ID=leon-gt-be98-lab\nNAME="GT-BE98 offline systemd lab"\n' > /newroot/tmp/etc/os-release
: > /newroot/tmp/etc/fstab
ln -s /proc/self/mounts /newroot/tmp/etc/mtab
cat > /newroot/tmp/etc/systemd/journald.conf <<'EOF'
[Journal]
Storage=volatile
RuntimeMaxUse=8M
ForwardToSyslog=no
EOF
cat > /newroot/tmp/etc/systemd/system.conf <<'EOF'
[Manager]
DefaultTimeoutStartSec=20s
DefaultTimeoutStopSec=10s
DefaultCPUAccounting=no
DefaultMemoryAccounting=yes
DefaultTasksAccounting=yes
RuntimeWatchdogSec=0
RebootWatchdogSec=0
EOF
unset LD_LIBRARY_PATH LD_PRELOAD
chroot /newroot /usr/sbin/ldconfig
echo LAB_SYSTEMD_EXEC_PID1
trap - EXIT
exec switch_root /newroot /usr/lib/systemd/systemd --system --unit=leon-lab.target --log-target=console --log-level=info --show-status=yes
