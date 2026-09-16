#!/usr/bin/bash
set -euo pipefail
work=/tmp/leon-ldd-verify-20260916
test -d "$work"
unset LD_PRELOAD LD_LIBRARY_PATH
test "$(sha256sum "$work/abi-probe-armhf" | cut -d ' ' -f 1)" = 2c85ee23010aaa0d180c17d2fb38a0f8316045c39c5c8bac431e0ca030d1b1eb
count=0
for entry in /usr/bin/ldd /usr/local/bin/ldd /opt/bin/ldd; do
  for case in aarch64 armel vendor-rc armhf entware-aarch64; do
    case "$case" in
      aarch64) target=/usr/bin/bash; expected=/usr/lib/aarch64-linux-gnu/libc.so.6;;
      armel) target=/bin/busybox; expected=/usr/lib/arm-linux-gnueabi/libc.so.6;;
      vendor-rc) target=/usr/sbin/rc; expected=/usr/lib/arm-linux-gnueabi/libc.so.6;;
      armhf) target="$work/abi-probe-armhf"; expected=/usr/lib/arm-linux-gnueabihf/libc.so.6;;
      entware-aarch64) target=/opt/bin/bash; expected=/opt/lib/libc.so.6;;
    esac
    "$entry" "$target" > "$work/output.txt" 2>&1
    grep -Fq "$expected" "$work/output.txt"
    if grep -Fq 'not found' "$work/output.txt"; then cat "$work/output.txt"; exit 1; fi
    printf 'LDD_CASE_PASS %s %s\n' "$entry" "$case"
    count=$((count+1))
  done
  "$entry" -v -- /bin/busybox "$work/abi-probe-armhf" > "$work/verbose.txt" 2>&1
  grep -Fq /usr/lib/arm-linux-gnueabi/libc.so.6 "$work/verbose.txt"
  grep -Fq /usr/lib/arm-linux-gnueabihf/libc.so.6 "$work/verbose.txt"
  if "$entry" "$work/does-not-exist" > "$work/missing.txt" 2>&1; then exit 1; fi
done
test "$count" = 15
for prefix in /usr/local/bin /opt/bin; do
  PATH="$prefix:$PATH" ldd /bin/busybox > "$work/path.txt"
  grep -Fq /usr/lib/arm-linux-gnueabi/libc.so.6 "$work/path.txt"
  printf 'LDD_PATH_PASS %s\n' "$prefix"
done
/usr/gnu/bin/timeout 15 /usr/bin/bash --login -c \
  'type -a ldd; ldd /bin/busybox' > "$work/login.txt" 2>&1
grep -Fq /usr/lib/arm-linux-gnueabi/libc.so.6 "$work/login.txt"
printf 'LDD_FRESH_LOGIN_PASS\n'
ls -l /usr/local/bin/ldd /opt/bin/ldd
sha256sum /usr/bin/ldd /usr/local/bin/ldd /opt/bin/ldd
printf 'LDD_VERIFY_COMPLETE cases=%s\n' "$count"
