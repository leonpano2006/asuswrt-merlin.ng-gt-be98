#!/usr/bin/bash
# Exercise only bounded child processes with explicit library paths in RAM.
set -euo pipefail
work=/tmp/leon-a53-runtime-verify-20260916
test -d "$work"
unset LD_PRELOAD LD_LIBRARY_PATH
ulimit -c 0
test "$(nvram get productid)" = GT-BE98
test "$(uname -r)" = 4.19.294
case "$(uname -v)" in '#36 '*) ;; *) exit 1;; esac
cd "$work"
sha256sum -c probe-files.sha256
sha256sum -c baseline.sha256
bcm_bootstate > bootstate-before.txt
/bin/fc status > acceleration-before.txt
for abi in aarch64 armel armhf armel-legacy aarch64-legacy; do
  case "$abi" in
    aarch64|aarch64-legacy) loader=/lib/ld-linux-aarch64.so.1; triplet=aarch64-linux-gnu;;
    armel|armel-legacy) loader=/lib/ld-linux.so.3; triplet=arm-linux-gnueabi;;
    armhf) loader=/lib/ld-linux-armhf.so.3; triplet=arm-linux-gnueabihf;;
  esac
  library_path="$work/runtime/$triplet:/usr/lib/$triplet"
  printf 'LIVE_A53_BEGIN %s\n' "$abi"
  EXPECTED_TRIPLET="$triplet" /usr/gnu/bin/timeout 20 \
    "$loader" --inhibit-cache --library-path "$library_path" "$work/bin/runtime-$abi"
  /usr/gnu/bin/timeout 20 "$loader" --inhibit-cache --library-path "$library_path" \
    "$work/bin/exception-$abi" "$work/bin/throw-$abi.so"
  for stringabi in 0 1; do
    EXPECTED_TRIPLET="$triplet" /usr/gnu/bin/timeout 20 \
      "$loader" --inhibit-cache --library-path "$library_path" "$work/bin/cxx-$abi-abi$stringabi"
  done
  printf 'LIVE_A53_COMPLETE %s\n' "$abi"
done
/usr/gnu/bin/timeout 20 /lib/ld-linux.so.3 --inhibit-cache \
  --library-path "$work/runtime/arm-linux-gnueabi:/usr/lib/arm-linux-gnueabi" "$work/bin/library-probe"
sha256sum -c baseline.sha256
bcm_bootstate > bootstate-after.txt
/bin/fc status > acceleration-after.txt
cmp bootstate-before.txt bootstate-after.txt
cat acceleration-before.txt acceleration-after.txt
printf 'LIVE_A53_ISOLATED_PASS\n'
