#!/bin/sh
set -eu
USB=/tmp/mnt/JFFS
OLD=$USB/gcc-16.1.0-backup-20260914
test -d "$OLD"
test -L "$USB/gcc16"
test "$(readlink "$USB/gcc16")" = gcc-16.2.0-usb
unlink "$USB/gcc16"
mv "$OLD" "$USB/gcc16"
"$USB/gcc16/bin/gcc" --version | head -n 1
