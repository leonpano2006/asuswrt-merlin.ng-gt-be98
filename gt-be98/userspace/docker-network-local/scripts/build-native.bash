#!/usr/bin/env bash
# Run on the AArch64 DGX, never on the router.
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
[ "$(uname -m)" = aarch64 ]
cc=${CC:-/usr/bin/gcc-13}
mkdir -p "$root/downloads" "$root/build" "$root/evidence"
archive="$root/downloads/iptables-1.8.13.tar.xz"
if [ ! -f "$archive" ]; then
    curl --fail --location --proto '=https' --tlsv1.2 -o "$archive" https://www.netfilter.org/projects/iptables/files/iptables-1.8.13.tar.xz
fi
echo "1afcd33da9e8f913ace6a2126788162e207e26f5d5e29c6573c0e581ffc58b99  $archive" | sha256sum -c -
src=$(mktemp -d "$root/build/iptables-build.XXXXXXXX")
tar -xf "$archive" -C "$src" --strip-components=1
cd "$src"
./configure --prefix=/usr/local/libexec/docker/iptables --disable-nftables --disable-shared --enable-static --disable-devel CC="$cc" CFLAGS='-O2 -mcpu=cortex-a53' LDFLAGS=-static > "$root/evidence/iptables-configure.log" 2>&1
make -j8 LDFLAGS=-all-static > "$root/evidence/iptables-build.log" 2>&1
cp iptables/xtables-legacy-multi "$root/build/xtables-legacy-multi"
"$cc" -static -O2 -mcpu=cortex-a53 -Wall -Wextra -Werror -o "$root/build/docker-root-view" "$root/scripts/docker-root-view.c"
strip "$root/build/xtables-legacy-multi" "$root/build/docker-root-view"
qemu-aarch64 -cpu cortex-a53 "$root/build/xtables-legacy-multi" iptables --version
# The helper should reach its firmware guard, not die on an ISA mismatch.
set +e
qemu-aarch64 -cpu cortex-a53 "$root/build/docker-root-view" --probe
rc=$?
set -e
[ "$rc" = 90 ]
sha256sum "$root/build/xtables-legacy-multi" "$root/build/docker-root-view"
