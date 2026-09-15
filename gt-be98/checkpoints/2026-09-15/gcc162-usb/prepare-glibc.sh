#!/bin/sh
set -eu
TASK=/tmp/mnt/JFFS/gcc162-update-20260914
LIB=/opt/lib.leon244-20260914
INC=/opt/include.leon244-20260914
FW=/lib/aarch64-linux-gnu
BB=/bin/busybox
test ! -e "$LIB"
test ! -e "$INC"
test -r "$TASK/dev244/include/features.h"
$BB cp -a /opt/lib "$LIB"
$BB cp -a /opt/include "$INC"
# Replace glibc header directories as units; keep third-party and Linux headers.
for d in bits gnu sys; do $BB rm -rf "$INC/$d"; done
$BB cp -a "$TASK/dev244/include/." "$INC/"

SONAMES='ld-linux-aarch64.so.1 libc.so.6 libm.so.6 libmvec.so.1 libpthread.so.0 librt.so.1 libdl.so.2 libutil.so.1 libanl.so.1 libresolv.so.2 libnsl.so.1 libcrypt.so.1 libBrokenLocale.so.1 libnss_compat.so.2 libnss_db.so.2 libnss_dns.so.2 libnss_files.so.2 libnss_hesiod.so.2 libthread_db.so.1 libmemusage.so libpcprofile.so libc_malloc_debug.so.0'
for dst in "$LIB" "$LIB/gcc/aarch64-openwrt-linux-gnu/8.4.0"; do
    test -d "$dst" || continue
    # Legacy implementations without a firmware replacement are archived in
    # the untouched original directory. No installed ELF dependency was found
    # on libcidn; NIS is not configured in the firmware NSS configuration.
    for f in "$dst"/*-2.27.so "$dst"/libcidn.so* "$dst"/libnss_nis.so* "$dst"/libnss_nisplus.so* "$dst"/libSegFault.so; do
        if [ -e "$f" ] || [ -L "$f" ]; then $BB rm "$f"; fi
    done
    for name in $SONAMES; do
        test -e "$FW/$name"
        $BB ln -snf "$FW/$name" "$dst/$name"
    done
    # Install matching startup objects, linker scripts and static archives.
    # These development files are absent from the read-only firmware.
    for f in "$TASK/dev244/lib/"*; do
        test -f "$f" || continue
        name=${f##*/}
        case "$name" in
            *.a|*.o) $BB rm -f "$dst/$name"; $BB cp "$f" "$dst/$name" ;;
        esac
    done
    for name in libc.so libm.so; do
        $BB rm -f "$dst/$name"
        $BB cp "$TASK/dev244/lib/$name" "$dst/$name"
    done
    for pair in 'libcrypt.so libcrypt.so.1' 'libresolv.so libresolv.so.2' 'libanl.so libanl.so.1' 'libnsl.so libnsl.so.1' 'libBrokenLocale.so libBrokenLocale.so.1' 'libmvec.so libmvec.so.1' 'libthread_db.so libthread_db.so.1'; do
        set -- $pair
        $BB ln -snf "$FW/$2" "$dst/$1"
    done
    # glibc >=2.34 folds these into libc and supplies compatibility archives.
    for name in pthread dl rt util; do
        $BB rm -f "$dst/lib$name.so"
        printf 'GROUP ( libc.so.6 )\n' > "$dst/lib$name.so"
    done
    for name in compat db dns files hesiod; do
        $BB ln -snf "$FW/libnss_$name.so.2" "$dst/libnss_$name.so"
    done
done
# Remove the old absolute-path aliases; the loader's stable pathname remains.
printf 'GLIBC244_STAGED\n'
