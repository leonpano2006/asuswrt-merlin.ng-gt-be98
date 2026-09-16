#!/usr/bin/bash
# Run only child-process probes against libraries in this temporary directory.
set -euo pipefail
work=/tmp/leon-libgcc-verify-20260916
test -d "$work"
unset LD_PRELOAD LD_LIBRARY_PATH
ulimit -c 0
test "$(nvram get productid)" = GT-BE98
test "$(uname -r)" = 4.19.294
case "$(uname -v)" in '#36 '*) ;; *) exit 1;; esac
cd "$work"
sha256sum -c probe-files.sha256
sha256sum -c baseline.sha256
test ! -e /usr/lib/arm-linux-gnueabihf/libgcc_s.so.1
bcm_bootstate > bootstate-before.txt
/bin/fc status > acceleration-before.txt
for abi in aarch64 armel armhf armel-legacy; do
  case "$abi" in
    aarch64) loader=/lib/ld-linux-aarch64.so.1; triplet=aarch64-linux-gnu;;
    armel|armel-legacy) loader=/lib/ld-linux.so.3; triplet=arm-linux-gnueabi;;
    armhf) loader=/lib/ld-linux-armhf.so.3; triplet=arm-linux-gnueabihf;;
  esac
  library_path="$work/runtime/$triplet:/usr/lib/$triplet"
  printf 'LIVE_LIBGCC_BEGIN %s\n' "$abi"
  EXPECTED_TRIPLET="$triplet" /usr/gnu/bin/timeout 20 \
    "$loader" --inhibit-cache --library-path "$library_path" "$work/bin/runtime-$abi"
  /usr/gnu/bin/timeout 20 "$loader" --inhibit-cache --library-path "$library_path" \
    "$work/bin/exception-$abi" "$work/bin/throw-$abi.so"
  printf 'LIVE_LIBGCC_COMPLETE %s\n' "$abi"
done
sha256sum -c baseline.sha256
test ! -e /usr/lib/arm-linux-gnueabihf/libgcc_s.so.1
bcm_bootstate > bootstate-after.txt
/bin/fc status > acceleration-after.txt
cmp bootstate-before.txt bootstate-after.txt
cat acceleration-before.txt acceleration-after.txt
printf 'LIVE_LIBGCC_ISOLATED_PASS\n'
