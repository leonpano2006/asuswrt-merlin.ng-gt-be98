# Preserved USB GCC 16.2.0 / glibc 2.44 deployment

Completed 2026-09-14 on the Leon firmware. GCC/G++ and their runtimes were
built on the AArch64 GB10 host, then installed to
`/tmp/mnt/JFFS/gcc-16.2.0-usb`; `gcc16` points there. Existing `gcc-16` and
`g++-16` entries continue to work. Target is
`aarch64-unknown-linux-gnu`, Cortex-A53+crypto+crc, sysroot `/opt`.
Entware's unversioned `/opt/bin/gcc` remains GCC 8.4.

The firmware's 64-bit runtime is `/lib/aarch64-linux-gnu`, while the
top-level `/lib/libc.so.6` is ARM32. `/opt/lib` runtime SONAMEs, including
old GCC 8.4 directory copies, were changed to use the AArch64 firmware
glibc 2.44 and libxcrypt. Matching 2.44 headers, startup objects, linker
scripts and archives remain on USB. Linker scripts use relative names;
the new GCC specs use `/opt/lib/ld-linux-aarch64.so.1` and search its own
lib64 before Entware's old C++ runtime. This deployment does not implement
a global usr-merge or move armel libraries into multiarch paths.

`build.sh` and `package.py` preserve the recipe. Inputs not stored here are
the GNU GCC 16.2.0 source/prerequisites, an `obj/` directory and a prepared
`sysroot/` containing the router's runtime plus matching glibc development
files. The bootstrap compiler is GCC/G++ 13, build/host/target are all
AArch64, and installation is staged through DESTDIR. It is not a full
bootstrap or an upstream GCC testsuite run.

The shell deployment scripts are the **original dated operation**, with
the original USB paths and backup names. They require the development
payload, static `exchange` helper, original precheck logs and a compatible
filesystem. They are retained for review/reproduction after preparing
those inputs; do not blindly rerun activation on the completed install.
`prepare-glibc.sh` stages a copy; `activate-glibc.sh` exchanges directories
using renameat2(RENAME_EXCHANGE) and retains the old runtime/headers.
`rollback-all.sh` restores GCC first, then glibc/headers and ldd. Existing
Entware package metadata was backed up and libc/libpthread/librt/gcc held
to prevent ordinary upgrades overwriting this custom runtime.

Validation: 1,624 installed file hashes matched. Before activation 88
Entware ELF loader checks passed; after activation all 86 remaining `/opt`
interpreter executables passed (the two new compilers use the firmware
interpreter). Bash, Make, binutils, GCC8, Git, Perl DNS and crypt worked.
C17 and C++20 tests, each with and without LTO, passed and reported
GCC 16.2.0/glibc 2.44. C++ dependency resolution used the new libstdc++ and
libgcc_s. The old GCC 16.1 backup remained executable.

Installed package SHA-256:
`58d311cd5c95f7df0adee9e1bbc0383e82841cd81340d53c8740057d49a47fe6`.

This update did not rebuild or flash firmware. It depends on the existing
Leon glibc 2.44 layer and must not be assumed compatible with stock ASUS
or a fallback image containing an older runtime.
