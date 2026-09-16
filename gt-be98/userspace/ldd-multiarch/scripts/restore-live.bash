#!/usr/bin/bash
# Explicit undo: verify both links and the preserved old file before changing.
set -euo pipefail
backup=/usr/local/share/leon-backups/ldd-20260916/opt-bin-ldd
test "$(readlink /opt/bin/ldd)" = /usr/bin/ldd
test "$(readlink /usr/local/bin/ldd)" = /usr/bin/ldd
test "$(sha256sum "$backup" | cut -d ' ' -f 1)" = af1ef718ebc9d104434124eca35a08f391af73899685dc4ca308f43685d6f5c7
test ! -e /opt/bin/ldd.leon-restore && test ! -L /opt/bin/ldd.leon-restore
cp -p "$backup" /opt/bin/ldd.leon-restore
/usr/gnu/bin/coreutils --coreutils-prog=mv -Tf /opt/bin/ldd.leon-restore /opt/bin/ldd
rm /usr/local/bin/ldd
printf 'Previous /opt/bin/ldd restored; added /usr/local/bin/ldd removed.\n'
