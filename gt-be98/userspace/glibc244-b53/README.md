# glibc 2.44 for GT-BE98 Brahma-B53

Rebuilt on an AArch64 DGX host from the same deployed glibc revision:
`2d5421ffca8893534d5e02ad38c28acd8e778fa3` on
<https://sourceware.org/git/glibc.git> (`release/2.44/master`).
The source reports stable **2.44** and was not patched. `--enable-kernel=4.19`
is retained. The older external pipeline already requested Cortex-A53;
this recipe makes the B53 alias explicit, preserves its inputs and verifies
new output. No performance improvement over that older build is claimed.

The router reports MIDR `0x420f1000`: Broadcom implementer `0x42`, part
`0x100`. Its exposed ISA is ARMv8.0-A with FP/NEON, AES, PMULL, SHA1, SHA2
and CRC32. AArch64 HWCAP is `0x8ff`, HWCAP2 is zero; neither LSE nor SVE
is advertised. ARM32 HWCAP is `0x37b0d6`, HWCAP2 is `0x1f`.

| ABI | Compiler CPU flags | GCC used | Runtime libraries |
|---|---|---|---|
| AArch64 | `-mcpu=cortex-a53+crypto+crc` | 16.2.0 | `/lib/aarch64-linux-gnu` |
| armel | `-mcpu=cortex-a53 -mfpu=crypto-neon-fp-armv8 -mfloat-abi=softfp` | 13.3.0 | `/lib` |
| armhf | `-mcpu=cortex-a53 -mfpu=crypto-neon-fp-armv8 -mfloat-abi=hard` | 13.3.0 | `/lib/arm-linux-gnueabihf` |

All builds use `-O2 -g`. `--cpu b53`, `--cpu brahma-b53` and
`--cpu cortex-a53` resolve to Cortex-A53 compiler settings. They do not
rewrite hardware MIDR or glibc's runtime feature detection. Higher-ISA
implementations retained in glibc multiarch objects have runtime guards;
their presence alone is not evidence that the default ISA was raised.

## Out-of-source build

The firmware source tree does not contain these build outputs. Keep this
recipe in Git and pass independent source, output and toolchain locations.
glibc 2.44 requires GCC >= 12.1 and binutils >= 2.39. The existing Buildroot
GCC 10.3 kernel compiler is unsuitable for this build. Exported Linux 4.19
UAPI headers were taken from the separately released
[am-toolchains-aarch64 SDK](https://github.com/leonpano2006/am-toolchains-aarch64/releases/tag/v2021.02.4-1);
the SDK and Buildroot sources remain in that repository.

Prepare the pinned source:

```sh
git init /path/to/glibc-source
git -C /path/to/glibc-source remote add origin https://sourceware.org/git/glibc.git
git -C /path/to/glibc-source fetch --depth 1 origin 2d5421ffca8893534d5e02ad38c28acd8e778fa3
git -C /path/to/glibc-source checkout --detach FETCH_HEAD
```

Build each ABI on the DGX (or another AArch64 host), for example:

```sh
python3 scripts/build-glibc.py --source /path/to/glibc-source \
  --output /path/to/work/builds/aarch64 --abi aarch64 --cpu b53 \
  --cc /path/to/gcc-16.2/bin/gcc --cxx /path/to/gcc-16.2/bin/g++ \
  --headers /path/to/aarch64-sdk/sysroot/usr/include --jobs 6

python3 scripts/build-glibc.py --source /path/to/glibc-source \
  --output /path/to/work/builds/armel --abi armel --cpu b53 \
  --cc /path/to/arm-linux-gnueabi-gcc --cxx /path/to/arm-linux-gnueabi-g++ \
  --headers /path/to/arm-sdk/sysroot/usr/include --jobs 3

python3 scripts/build-glibc.py --source /path/to/glibc-source \
  --output /path/to/work/builds/armhf --abi armhf --cpu b53 \
  --cc /path/to/arm-linux-gnueabihf-gcc --cxx /path/to/arm-linux-gnueabihf-g++ \
  --headers /path/to/arm-sdk/sysroot/usr/include --jobs 3
```

Compiler arguments such as `-B` or `--sysroot` can be included in a quoted
`--cc`/`--cxx` value. Relocated Ubuntu cross-binutils may additionally need
`--host-library-dir /path/to/package-root/usr/lib/aarch64-linux-gnu` for
their native libbfd dependencies. The ARM32 package versions and hashes
are retained in `evidence/arm32-toolchain-packages.json`.

`build-glibc.py` installs only with `DESTDIR` into each output's `stage/`.
It leaves the source, host glibc and router glibc alone. Do not run a plain
`make install` into the DGX root. A completed output can be resumed only
with the same recorded configuration; use a fresh output for changed flags.

## Validation and artifacts

All three builds completed configure, make and staged install. Each passed
memory alignment/overlap and allocation, pthread/TLS/mutex, libm, getrandom,
clock, numeric resolver and gconv smoke tests. AArch64 user-mode QEMU used
`cortex-a53`; ARM user-mode QEMU used `max` because that executable does not
provide an A53 model. **All three ABIs also passed on the actual B53**, using
explicit loaders from a dedicated `/tmp` directory under kernel 4.19.294 #36.
The installed system glibc hashes were unchanged before/after testing.

Nine libraries (libc/libm/libresolv across three ABIs) retained all existing
public versioned symbols. ARM32 ELF attributes retain ARMv8/NEON and the
correct softfp versus VFP-register calling conventions. Six upstream
string tests passed under Cortex-A53 QEMU: memcpy, memmove, memset,
memcmp, strlen and strcmp. This is a bounded test subset, not the complete
upstream glibc suite or a long-term firmware stability result.

For repeatable smoke tests, copy `tests/` to `/path/to/work/tests/`, then:

```sh
python3 scripts/smoke-qemu.py --work /path/to/work
python3 scripts/package-runtime.py --work /path/to/work
```

The packager retains `/lib/ld-linux-aarch64.so.1` and
`/lib/ld-linux-armhf.so.3` as relative links to their existing multiarch
loader locations; armel's loader stays `/lib/ld-linux.so.3`. It strips
copies, retaining unstripped build outputs. It produces a zstd-22 runtime
archive and a gzip transport copy for the router's existing tar utility.
The runtime archive contains libraries and gconv modules; complete staged
installs separately retain headers, archives, startup objects and utilities.
The utility paths and runtime package are not automatically installed.

This build has not been integrated into or flashed as a new firmware image.
Integration must recheck image size and the active/fallback slot state.
The recorded archive hashes identify the validated outputs; changed build
paths/toolchain/header versions are not claimed to be byte-identical.

GCC flag semantics: [AArch64 options](https://gcc.gnu.org/onlinedocs/gcc/AArch64-Options.html),
[ARM options](https://gcc.gnu.org/onlinedocs/gcc/ARM-Options.html).
