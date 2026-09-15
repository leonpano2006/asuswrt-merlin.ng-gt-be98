#!/bin/sh
set -eu
USB=/tmp/mnt/JFFS
NEW=$USB/gcc-16.2.0-usb
OLD=$USB/gcc-16.1.0-backup-20260914
test -d "$NEW"
test -d "$USB/gcc16"
test ! -L "$USB/gcc16"
test ! -e "$OLD"
test ! -e "$USB/.gcc16-next"
grep -q ALL_GCC162_TESTS_PASSED "$NEW/tests/results.log"
test "$("$NEW/bin/gcc" -dumpfullversion)" = 16.2.0
ln -s gcc-16.2.0-usb "$USB/.gcc16-next"
mv "$USB/gcc16" "$OLD"
if ! mv "$USB/.gcc16-next" "$USB/gcc16"; then
    mv "$OLD" "$USB/gcc16"
    exit 1
fi
"$USB/gcc16/bin/gcc" --version | head -n 1
printf 'Old compiler preserved: %s\n' "$OLD"
