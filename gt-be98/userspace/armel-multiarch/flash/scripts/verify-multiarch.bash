#!/usr/bin/bash
set -eu
work=/tmp/leon-armel-verify
test -d "$work"
test "$(readlink /lib)" = usr/lib
test "$(readlink /usr/lib/ld-linux.so.3)" = arm-linux-gnueabi/ld-linux.so.3
test "$(readlink /usr/lib/libnvram.so)" = arm-linux-gnueabi/libnvram.so
test "$(sha256sum /usr/lib/arm-linux-gnueabi/libnvram.so | cut -d ' ' -f 1)" = 45066c6af9c9a8b843057b6d7bc341a49e3b90fae3d381d06a5f99bb54517b00
grep -Fxq 'include /etc/ld.so.conf.d/*.conf' /etc/ld.so.conf
for triplet in arm-linux-gnueabi arm-linux-gnueabihf aarch64-linux-gnu; do
    grep -Fxq "/usr/lib/$triplet" "/etc/ld.so.conf.d/$triplet.conf"
done
sha256sum -c "$work/libraries.sha256"
"$work/library-probe"
for abi in aarch64 armel armhf; do
    "$work/abi-probe-$abi"
done
count=0
failed=0
while read -r loader program; do
    count=$((count + 1))
    if ! "$loader" --list "$program" > "$work/linker.out" 2>&1; then
        printf 'LINKER_FAILURE %s\n' "$program"
        cat "$work/linker.out"
        failed=$((failed + 1))
    fi
done < "$work/dynamic-executables.txt"
printf 'LIVE_LINKER_SUMMARY count=%s failed=%s\n' "$count" "$failed"
test "$count" = 312 && test "$failed" = 0
/usr/sbin/ldconfig -p | grep -E 'libz\.so\.1|libexpat\.so\.1|libjson-c\.so\.2|libcap-ng\.so\.0'
echo ARMEL_MULTIARCH_LIVE_LIBRARIES_PASS
