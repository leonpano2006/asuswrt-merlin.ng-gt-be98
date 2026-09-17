#!/usr/bin/bash
# Replace only less-package entries on read-only merged-/usr firmware.
# A bind mount onto the original less symlink would cover BusyBox: never do it.
set -euo pipefail
export PATH=/usr/bin:/usr/sbin:/bin:/sbin
mode=${1:-apply}
case "$mode" in apply|check) ;; *) exit 2 ;; esac
payload=$(cd -- "$(dirname -- "$0")" && pwd -P)
state=/run/leon-less-704
lock=/run/leon-less-704.lock
busybox_sha=73cc3ca6beba4672e94053551cc7c5fe2dd92698e580f91a031cbff959600b4e

# Native firmware installations, including subsequent versions, need no overlay.
if [ ! -L /usr/bin/less ] && /usr/bin/less --version 2>/dev/null | grep -q '^less [0-9]'; then
    exit 0
fi
# Do not change the committed fallback or an unrelated firmware installation.
grep -q '3006.102.9-beta1-leon3' /usr/share/leon-upstream.json || exit 0
grep -q '#36 ' /proc/version || exit 0
[ "$(readlink /bin)" = usr/bin ]
[ "$(readlink /usr/bin/less)" = ../../bin/busybox ]
[ "$(sha256sum /usr/bin/busybox | cut -d' ' -f1)" = "$busybox_sha" ]
if awk '$2=="/usr/bin" {found=1} END {exit !found}' /proc/mounts; then
    echo 'An existing /usr/bin mount needs review; refusing to cover it.' >&2
    exit 1
fi
mkdir -m 700 "$lock" || exit 0
trap 'rmdir "$lock"' EXIT
cd "$payload"
sha256sum -c SHA256SUMS
./bin/less --version | grep -q '^less 704 '
mkdir -p "$state"/{original,package,check}
chmod 700 "$state"
cp -p bin/* "$state/package/"
chmod 755 "$state/package"
mount --bind /usr/bin "$state/original"
mount --make-private "$state/original"
mount -o remount,bind,ro "$state/original"
check_mounted=no
live_mounted=no
cleanup() {
    if [ "$check_mounted" = yes ]; then umount "$state/check"; fi
    if [ "$live_mounted" = no ]; then umount "$state/original"; fi
}
trap 'cleanup; rmdir "$lock"' EXIT
opts="ro,lowerdir=$state/package:$state/original"
mount -t overlay -o "$opts" leon-less-704 "$state/check"
check_mounted=yes
[ ! -L "$state/check/less" ]
[ "$(sha256sum "$state/check/busybox" | cut -d' ' -f1)" = "$busybox_sha" ]
"$state/check/busybox" true
"$state/check/less" --version | grep -q '^less 704 '
umount "$state/check"
check_mounted=no
if [ "$mode" = check ]; then
    echo 'LESS_PRIVATE_OVERLAY_CHECK_PASS'
    exit 0
fi
mount -t overlay -o "$opts" leon-less-704 /usr/bin
live_mounted=yes
if [ -L /usr/bin/less ] ||
   ! /usr/bin/less --version | grep -q '^less 704 ' ||
   [ "$(sha256sum /usr/bin/busybox | cut -d' ' -f1)" != "$busybox_sha" ]; then
    umount /usr/bin
    live_mounted=no
    exit 1
fi
logger -t leon-less 'Full less 704 available at /usr/bin/less (read-only RAM overlay).'
echo 'LESS_LIVE_INSTALL_PASS'
