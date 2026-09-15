#!/bin/sh
set -eu
GCC_USB_PREFIX=${GCC_USB_PREFIX:-/tmp/mnt/JFFS/gcc-16.2.0-usb}
cd "$(dirname "$0")"
export PATH="$GCC_USB_PREFIX/bin:/opt/bin:/usr/bin:/bin:/usr/sbin:/sbin"
unset LD_LIBRARY_PATH GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH
gcc --version | head -n 1
g++ --version | head -n 1
gcc -print-sysroot
gcc -Q --help=target | grep -E 'mcpu=|march=|mtune='
gcc -O2 -std=c17 -Wall -Wextra -Werror test.c -pthread -lm -o test-c
./test-c
g++ -O2 -std=c++20 -Wall -Wextra -Werror test.cpp -pthread -o test-cpp
./test-cpp
gcc -O2 -std=c17 -flto test.c -pthread -lm -o test-c-lto
./test-c-lto
g++ -O2 -std=c++20 -flto test.cpp -pthread -o test-cpp-lto
./test-cpp-lto
printf '\nELF runtime configuration\n'
for f in test-c test-cpp; do
    readelf -l "$f" | grep interpreter
    readelf -d "$f" | grep -E 'NEEDED|RPATH|RUNPATH'
done
printf '\nALL_GCC162_TESTS_PASSED\n'
