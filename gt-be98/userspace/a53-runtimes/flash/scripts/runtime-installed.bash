#!/usr/bin/bash
# Test the installed firmware libraries through each executable's normal loader.
set -euo pipefail
unset LD_PRELOAD LD_LIBRARY_PATH
ulimit -c 0
work=/tmp/leon-a53-flash-verify
cd "$work"
sha256sum -c installed-libraries.sha256
for abi in aarch64 armel armhf armel-legacy aarch64-legacy; do
    case "$abi" in
        aarch64|aarch64-legacy) triplet=aarch64-linux-gnu;;
        armel|armel-legacy) triplet=arm-linux-gnueabi;;
        armhf) triplet=arm-linux-gnueabihf;;
    esac
    printf 'INSTALLED_RUNTIME_BEGIN %s\n' "$abi"
    EXPECTED_TRIPLET="$triplet" /usr/gnu/bin/timeout 20 "$work/bin/runtime-$abi"
    /usr/gnu/bin/timeout 20 "$work/bin/exception-$abi" "$work/bin/throw-$abi.so"
    for stringabi in 0 1; do
        EXPECTED_TRIPLET="$triplet" /usr/gnu/bin/timeout 20 "$work/bin/cxx-$abi-abi$stringabi"
    done
    printf 'INSTALLED_RUNTIME_COMPLETE %s\n' "$abi"
done
/usr/bin/ldd /bin/busybox
/usr/bin/ldd /usr/bin/bash
echo A53_INSTALLED_RUNTIME_PASS
