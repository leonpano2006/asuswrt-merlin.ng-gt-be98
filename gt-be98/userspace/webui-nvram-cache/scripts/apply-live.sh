#!/bin/sh
# Apply only to the reviewed merged-/usr #36 firmware. No NVRAM or flash writes.
set -eu
BASE=/jffs/leon-webui-fix
TARGET=/usr/lib/libnvram.so
ORIGINAL=6eb214a9e4de1269d5467c8ac5d9f3ed4fdfda535d6546ea222fba44d0e35c46
PATCHED=45066c6af9c9a8b843057b6d7bc341a49e3b90fae3d381d06a5f99bb54517b00
hash() { /usr/bin/sha256sum "$1" | /usr/bin/cut -d ' ' -f 1; }

case "${1:-apply}" in
    apply)
        [ ! -f "$BASE/disabled" ] || exit 0
        [ "$(readlink /bin)" = usr/bin ] || exit 0
        [ "$(readlink /proc/1/exe)" = /usr/sbin/rc ] || exit 0
        case "$(uname -v)" in '#36 '*) ;; *) exit 0;; esac
        [ "$(hash "$BASE/libnvram.so")" = "$PATCHED" ]
        current=$(hash "$TARGET")
        [ "$current" != "$PATCHED" ] || exit 0
        [ "$current" = "$ORIGINAL" ] || {
            logger -t leon-webui-fix 'Skipped: unrecognized libnvram.so'
            exit 1
        }
        /bin/mount --bind "$BASE/libnvram.so" "$TARGET"
        if [ "$(hash "$TARGET")" != "$PATCHED" ]; then
            /bin/umount "$TARGET"
            exit 1
        fi
        logger -t leon-webui-fix 'Applied NVRAM cache getter fix; restarting management service'
        /sbin/service restart_httpd
        ;;
    revert)
        # Disable startup reapplication before removing the runtime overlay.
        : > "$BASE/disabled"
        if [ "$(hash "$TARGET")" = "$PATCHED" ]; then
            /bin/umount "$TARGET"
            [ "$(hash "$TARGET")" = "$ORIGINAL" ]
            /sbin/service restart_httpd
        fi
        ;;
    *) echo 'Usage: apply-live.sh [apply|revert]' >&2; exit 2;;
esac
