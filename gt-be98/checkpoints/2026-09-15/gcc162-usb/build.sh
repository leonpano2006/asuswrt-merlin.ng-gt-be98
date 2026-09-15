#!/bin/bash
set -euo pipefail
TASK_ROOT=$(cd -- "$(dirname -- "$0")" && pwd)
INSTALL_PREFIX=/tmp/mnt/JFFS/gcc-16.2.0-usb
cd "$TASK_ROOT/obj"
export CC=/usr/bin/gcc-13 CXX=/usr/bin/g++-13
export CFLAGS='-O2 -march=armv8-a+crypto+crc -mtune=cortex-a53'
export CXXFLAGS="$CFLAGS"
export LDFLAGS="-Wl,-rpath,$INSTALL_PREFIX/host-lib -Wl,-rpath,/lib/aarch64-linux-gnu"
"$TASK_ROOT/gcc-16.2.0/configure" \
  --prefix="$INSTALL_PREFIX" \
  --build=aarch64-unknown-linux-gnu \
  --host=aarch64-unknown-linux-gnu \
  --target=aarch64-unknown-linux-gnu \
  --with-pkgversion='Leon USB glibc 2.44 20260914' \
  --with-sysroot=/opt --with-build-sysroot="$TASK_ROOT/sysroot" \
  --with-native-system-header-dir=/include \
  --with-glibc-version=2.44 \
  --with-cpu=cortex-a53+crypto+crc \
  --enable-languages=c,c++ --disable-bootstrap --disable-multilib \
  --disable-nls --disable-libsanitizer --disable-werror \
  --enable-checking=release > "$TASK_ROOT/configure.log" 2>&1
make -j8 > "$TASK_ROOT/build.log" 2>&1
make install-strip DESTDIR="$TASK_ROOT/stage" > "$TASK_ROOT/install.log" 2>&1
echo GCC162_BUILD_COMPLETE
