#!/bin/sh
# Execute staged libraries in child processes; never install into the running rootfs.
set -eu
BASE=${1:?supply the dedicated /tmp/glibc244-b53-* directory}
case "$BASE" in /tmp/glibc244-b53-*) ;; *) exit 2 ;; esac
test "$(uname -m)" = aarch64
case "$(uname -r)" in 4.19.*) ;; *) exit 2 ;; esac
cd "$BASE"
test -d runtime && test -d tests
tar -xzf glibc-2.44-b53-runtime.tar.gz -C runtime
tar -xzf smoke-tests.tar.gz -C tests
echo LIVE_EXISTING_LIBC_BEFORE
sha256sum /lib/aarch64-linux-gnu/libc.so.6 /lib/libc.so.6 /lib/arm-linux-gnueabihf/libc.so.6
for abi in aarch64 armel armhf; do
    case "$abi" in
        aarch64) lib=lib/aarch64-linux-gnu; dev=usr/lib/aarch64-linux-gnu; ld=ld-linux-aarch64.so.1 ;;
        armel) lib=lib; dev=usr/lib; ld=ld-linux.so.3 ;;
        armhf) lib=lib/arm-linux-gnueabihf; dev=usr/lib/arm-linux-gnueabihf; ld=ld-linux-armhf.so.3 ;;
    esac
    echo "LIVE_ABI $abi"
    GCONV_PATH="$BASE/runtime/$dev/gconv" \
      "$BASE/runtime/$lib/$ld" --library-path "$BASE/runtime/$lib" \
      "$BASE/tests/libc-smoke-$abi"
done
echo LIVE_EXISTING_LIBC_AFTER
sha256sum /lib/aarch64-linux-gnu/libc.so.6 /lib/libc.so.6 /lib/arm-linux-gnueabihf/libc.so.6
echo GLIBC_B53_LIVE_COMPLETE
