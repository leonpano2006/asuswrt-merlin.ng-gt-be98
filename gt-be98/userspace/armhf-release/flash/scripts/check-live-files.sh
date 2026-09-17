#!/bin/sh
set -eu
test "$(sha256sum /usr/sbin/rc | cut -d " " -f1)" = ca786145c19101bbfd4bb540aff3fbd3895d7dc47a2a7d476319d0a4009226a8
test "$(sha256sum /usr/sbin/httpd | cut -d " " -f1)" = e1c6013f9e535cd76294a4acc814b5b985fb487e79dff60066b18d52cd8bf450
test "$(sha256sum /usr/lib/aarch64-linux-gnu/libstdc++.so.6.0.36 | cut -d " " -f1)" = 3b58d3a043e1247796fabb05f605ed359dcb5cb08df7a472e928ba9b28dc12be
test "$(sha256sum /usr/lib/arm-linux-gnueabi/libstdc++.so.6.0.34 | cut -d " " -f1)" = 8f113e3fd1d43c326ac3c2664bff7c0847d43b9b460c0f52a8139a80986ca4d0
test "$(sha256sum /usr/bin/zstd | cut -d " " -f1)" = 424375112717f9dc0e6de4c1af7c53ede2c81948ba18834b56102c9389a60eac
test "$(sha256sum /usr/gnu/bin/sqlite3 | cut -d " " -f1)" = 7f6f3925ddb700ae26b853bb1eae7e543764f6f0ed46ccb9d737724dc27d32b7
test "$(sha256sum /usr/libexec/openssl4 | cut -d " " -f1)" = e403467c96de5b131803cd55ac0bfc9af22efbbe0dda3f9690a7359a15d9a19b
awk '$2=="/tmp/mnt/JFFS" && $3=="btrfs"{ok=1}END{exit !ok}' /proc/mounts
readlink /usr/lib/arm-linux-gnueabihf
printf 'LIVE_FILES_SHA256_AND_USB_MOUNT_PASS\n'
