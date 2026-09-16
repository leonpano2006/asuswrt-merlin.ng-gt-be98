#!/usr/bin/bash
# Reuse the firmware's three-ABI ldd through both writable tool prefixes.
set -euo pipefail
unset LD_PRELOAD LD_LIBRARY_PATH
canonical=/usr/bin/ldd
legacy=/opt/bin/ldd
local_entry=/usr/local/bin/ldd
backup=/usr/local/share/leon-backups/ldd-20260916
old_sha=af1ef718ebc9d104434124eca35a08f391af73899685dc4ca308f43685d6f5c7
canonical_sha=251bf4507a2b1e6a5ad062bc88493d52f688dea5c4fcac2a199e5fc04247d732

digest() { sha256sum "$1" | cut -d ' ' -f 1; }
test "$(nvram get productid)" = GT-BE98
test "$(digest "$canonical")" = "$canonical_sha"
test -f "$legacy" && test ! -L "$legacy"
test "$(digest "$legacy")" = "$old_sha"
test ! -e "$local_entry" && test ! -L "$local_entry"
test ! -e "$legacy.leon-new" && test ! -L "$legacy.leon-new"
test ! -e "$backup"
awk '$5=="/usr/local" && $6 ~ /^rw,/ {found=1} END {exit !found}' /proc/self/mountinfo
test -w /usr/local/bin && test -w /opt/bin
test -x /usr/gnu/bin/coreutils

mkdir -p /usr/local/share/leon-backups
mkdir -m 700 "$backup"
cp -p "$legacy" "$backup/opt-bin-ldd"
test "$(digest "$backup/opt-bin-ldd")" = "$old_sha"

local_created=0
legacy_replaced=0
rollback() {
  rc=$?
  trap - EXIT
  if test "$rc" != 0; then
    if test "$legacy_replaced" = 1; then
      cp -p "$backup/opt-bin-ldd" "$legacy.leon-restore"
      /usr/gnu/bin/coreutils --coreutils-prog=mv -Tf "$legacy.leon-restore" "$legacy"
    fi
    if test "$local_created" = 1 && test "$(readlink "$local_entry")" = "$canonical"; then
      rm "$local_entry"
    fi
    if test -L "$legacy.leon-new"; then rm "$legacy.leon-new"; fi
  fi
  exit "$rc"
}
trap rollback EXIT
ln -s "$canonical" "$local_entry"
local_created=1
ln -s "$canonical" "$legacy.leon-new"
test "$(digest "$legacy")" = "$old_sha"
/usr/gnu/bin/coreutils --coreutils-prog=mv -Tf "$legacy.leon-new" "$legacy"
legacy_replaced=1
for entry in "$local_entry" "$legacy"; do
  test "$(readlink "$entry")" = "$canonical"
  test "$(digest "$entry")" = "$canonical_sha"
  "$entry" /bin/busybox | grep -F '/usr/lib/arm-linux-gnueabi/libc.so.6'
  "$entry" /usr/lib/arm-linux-gnueabihf/libm.so.6 | grep -F '/usr/lib/arm-linux-gnueabihf/libc.so.6'
  "$entry" /usr/bin/bash | grep -F '/usr/lib/aarch64-linux-gnu/libc.so.6'
done
printf 'LDD_MULTIARCH_INSTALL_PASS\n'
