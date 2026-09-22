#!/bin/bash
# Reversible overlay for the verified leon10 runtime only. Never writes NAND.
set -eu
base=/jffs/leon-busybox-time64
target=/usr/bin/busybox
original=73cc3ca6beba4672e94053551cc7c5fe2dd92698e580f91a031cbff959600b4e
fixed=b03a42e0748b1e6363acaf18a454133548011616d7380760906c1ccd70c1fe74
expected_rc=cf121058ede3661d8b5a9f3bc3e8aed2850d533205b71ccf20bcf3a46c221981
expected_libc=71aa729b56b22bdb0e90b8882afc4d4a76de52f0769edc89bdaa8cca84d2bfe9
expected_ld=46b4992f7cdf26c0ea9c4c079fe315f63bcb00e9bd2dadd0b66052ad16421421
hash() { local value; value=$(sha256sum "$1") || return; printf '%s' "${value%% *}"; }
case "${1:-apply}" in
    apply)
        [ -f "$base/disabled" ] && exit 0
        current=$(hash "$target")
        [ "$current" = "$fixed" ] && exit 0
        if [ "$current" != "$original" ] ||
           [ "$(hash /sbin/rc)" != "$expected_rc" ] ||
           [ "$(hash /usr/lib/arm-linux-gnueabi/libc.so.6)" != "$expected_libc" ] ||
           [ "$(hash /lib/ld-linux.so.3)" != "$expected_ld" ]; then
            printf 'BusyBox time64 overlay skipped: firmware/runtime differs.\n'
            exit 0
        fi
        [ "$(hash "$base/busybox-fixed")" = "$fixed" ]
        [ "$(hash "$base/busybox-original")" = "$original" ]
        # Mount a RAM copy so the system executable does not depend on USB
        # remaining present after this hook has completed.
        "$base/busybox-original" mkdir -p /run/leon-busybox-time64
        "$base/busybox-original" cp "$base/busybox-fixed" /run/leon-busybox-time64/busybox.new
        "$base/busybox-original" chmod 755 /run/leon-busybox-time64/busybox.new
        "$base/busybox-original" mv /run/leon-busybox-time64/busybox.new /run/leon-busybox-time64/busybox
        /run/leon-busybox-time64/busybox true
        "$base/busybox-original" mount --bind /run/leon-busybox-time64/busybox "$target"
        [ "$(hash "$target")" = "$fixed" ]
        printf 'BusyBox time64 overlay applied.\n'
        ;;
    undo)
        [ "$(hash "$target")" = "$fixed" ] || exit 0
        [ "$(hash "$base/busybox-original")" = "$original" ]
        # Existing applets may still execute the mounted inode. Detach the
        # path while letting those processes finish with their current image.
        "$base/busybox-original" umount -l "$target"
        [ "$(hash "$target")" = "$original" ]
        printf 'BusyBox time64 overlay removed.\n'
        ;;
    *) printf 'Usage: %s apply|undo\n' "$0" >&2; exit 2 ;;
esac
