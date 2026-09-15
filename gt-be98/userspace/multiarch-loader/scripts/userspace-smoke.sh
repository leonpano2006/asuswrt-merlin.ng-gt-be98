#!/bin/sh
# Runs only in the QEMU guest's /firmware chroot.
set -eu
export PATH=/usr/gnu/bin:/usr/sbin:/usr/bin:/sbin:/bin
test -f /tmp/QEMU_LAB_GUEST
unset LD_LIBRARY_PATH LD_PRELOAD
run() {
    echo "LAB_USERSPACE_BEGIN $*"
    "$@"
    echo "LAB_USERSPACE_PASS $*"
}
run /lib/ld-linux-aarch64.so.1 --version
run /lib/ld-linux.so.3 --version
run /bin/busybox echo armel-busybox-runs
run /usr/bin/bash --version
run /usr/gnu/bin/coreutils --coreutils-prog=ls --version
run /usr/gnu/bin/tar --version
run /usr/gnu/bin/find --version
run /usr/gnu/bin/xargs --version
run /usr/gnu/bin/jq --version
run /usr/gnu/bin/sqlite3 --version
run /usr/gnu/bin/socat -V
run /usr/bin/htop --version
run /usr/bin/nano --version
run /usr/bin/iperf3 --version
run /usr/bin/zstd --version
run /usr/sbin/btrfs version
run /usr/sbin/mkfs.xfs -V
run /usr/sbin/ebtables --version
run /usr/bin/getconf GNU_LIBC_VERSION
run /usr/bin/ldd /usr/bin/bash
run /usr/bin/ldd /bin/busybox
# Exercise the canonical command entries, including the GNU overrides.
run /bin/bash -c 'test "$BASH_VERSION"; printf "shell-path-ok\n"'
run /bin/tar --version
run /usr/bin/sha256sum /bin/busybox /usr/bin/bash
run /usr/bin/dropbearmulti dropbear -V
run /usr/sbin/avahi-daemon --version
run /usr/sbin/ip link add labveth0 type veth peer name labveth1
run /usr/sbin/ip link set labveth0 up
run /usr/sbin/ip link set labveth1 up
run /usr/sbin/ip link add link labveth0 name labmac0 type macvlan mode bridge
run /usr/sbin/ip link set labmac0 up
run /usr/sbin/ip -d link show labmac0
run /usr/sbin/ip link del labmac0
run /usr/sbin/ip link del labveth0
echo LAB_USERSPACE_COMPLETE
