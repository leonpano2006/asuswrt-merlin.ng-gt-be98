# GT-BE98 Ubuntu-style multiarch loaders

This candidate keeps glibc **2.44**, the B53-as-Cortex-A53 CPU policy, kernel
4.19.294 #36 and the existing three ABIs. It uses Ubuntu's multiarch loader,
`$LIB`, ldconfig and loader-entry layout, and removes 257 unnecessary armel
compatibility symlinks. It is packaged and QEMU verified, **not flashed**.
The router remains on the previous hardware-tested, uncommitted image.

## Ubuntu reference and implementation

The signed Ubuntu 26.04 `resolute` archive was verified before extracting
28 packages into the workspace. Native armhf and arm64 libc6/libc6-dev packages
and armel cross-sysroot packages were inspected. Ubuntu does not provide a
native armel release here; the armel reference is explicitly its official
cross package. No foreign-architecture package was installed on DGX.
`evidence/ubuntu-reference.json` records every package/index/source hash.

The Ubuntu glibc 2.43-2ubuntu2 Debian packaging provides these changes:

- `local-ld-multiarch.diff`: multiarch search directories precede the legacy
  flat paths, and `$LIB` expands to `lib/<triplet>`.
- `local-ldconfig-multiarch.diff`: ldconfig uses the same generated system
  directory list as the loader.
- `local-ldconfig-ignore-ld.so.diff`: preserve existing loader entry symlinks.

`patches/ubuntu-multiarch-glibc244.patch` adapts those changes to the pinned
2.44 revision `2d5421ffca8893534d5e02ad38c28acd8e778fa3`. It retains 2.44's
`ldconfig_parse_config` callback API; it does not downgrade libc to Ubuntu's
reference version. Original patch hashes and the resulting source-tree hash
are pinned in `configs/glibc-source.json`. The original loader/multiarch work
is by Aurelien Jarno and Steve Langasek, from Ubuntu/Debian's glibc packaging.
The upstream glibc licensing continues to apply.

For each of `arm-linux-gnueabi`, `arm-linux-gnueabihf`, and
`aarch64-linux-gnu`, the built-in lookup order is:

1. `/lib/<triplet>`
2. `/usr/lib/<triplet>`
3. `/lib`
4. `/usr/lib`

With `/lib -> usr/lib`, actual loaders and libraries live under
`/usr/lib/<triplet>`. The three `/lib/ld-linux*.so.*` ABI entry points remain
symlinks. `/etc/ld.so.conf.d/<triplet>.conf` matches Ubuntu's two configured
paths, `/usr/local/lib/<triplet>` and `/usr/lib/<triplet>`. The existing generic
local/Entware compatibility fragments remain for the router's USB environment.
The actual new loaders' diagnostics match the extracted Ubuntu reference for
all path fields and `$LIB`; only the glibc version remains 2.44.

ARM32 builds use the official Ubuntu GCC 15.2 arm64-host cross compilers.
AArch64 retains the separate GCC 16.2 toolchain. CPU flags remain Cortex-A53,
softfp for armel and hard-float for armhf, with the previously established
crypto/CRC ISA limits. `_TIME_BITS` and `_FILE_OFFSET_BITS` compiler defaults
are cleared for the legacy ARM32 ABI. Minimum kernel stays 4.19. Headers and
Buildroot toolchains remain dependencies of their own repository/checkpoint.

## Compatibility links retained

The 289 armel migration links become **32 explicitly justified entries**:

| Entries | Count | Reason |
| --- | ---: | --- |
| `ld-linux.so.3` | 1 | ELF interpreter ABI entry |
| `leon-trial-bootguard.so` | 1 | Existing static init's preload path |
| `libasd.so`, `libshn_pctrl.so` | 2 | ASUS/DPI consumers use absolute paths |
| OpenVPN PAM plugin, `pam_unix.so` | 2 | VPN configuration and OpenPAM module search |
| `ipsec`, `l2tp`, `libnl`, `netatalk`, `pppd`, `xtables` | 6 | Installed consumers reference private plugin directories |
| lighttpd `mod_*.so` | 20 | Existing lighttpd constructs paths from `/usr/lib` |

Each name and reason is in `configs/rootfs-policy.json`; removal is limited to
verified migration-created links. SONAME/development links remain alongside
the real libraries in their ABI directory. No general libc/zlib/etc. links
are retained merely to make early startup work. Existing unrelated ABI/data
entries, including the distinct flat AArch64 libebtc file, are preserved.

The overlay replaces 62 existing runtime/loader/ldconfig files as matched
builds and checks their public exported symbol ABI against the baseline.
All 182 kernel modules, vendor blobs, the Web UI NVRAM fix, PID 1 wrapper and
boot-metadata guard remain bytewise unchanged. Complete staged glibc installs
retain SDK files and gconv modules outside the firmware; the deployed runtime
component set is preserved rather than adding those unused components.

## Reproduction

Use an AArch64 build host with Python 3/pyelftools, make, GCC/binutils,
OpenSSL, lzop, squashfs-tools with zstd, QEMU system/user emulators, dpkg-deb,
gpgv and Ubuntu archive keys. Sibling checkpoint names below are their paths
in the firmware Git repository.

```sh
python3 scripts/fetch-ubuntu-reference.py \
  --previous-checkpoint ../armel-multiarch --output .
python3 scripts/prepare-source.py \
  --archive downloads/glibc-2.44-source.tar --output source/glibc
```

The source tar is `git archive` of the pinned glibc commit and is preserved
in the ML350 backup. Its exact hash is required. Build each ABI with
`scripts/build-glibc.py`, giving the prepared source, a fresh `builds/<abi>`
output, matching compiler commands, exported Linux 4.19 headers, and bounded
parallelism. The three recorded configurations and commands are in `evidence/`.
Use the armel toolchain from the sibling checkpoint, the newly extracted
`toolchain-armhf`, and the existing GCC 16.2 AArch64 toolchain. The builder
verifies the complete prepared source tree and uses only staged `DESTDIR`
installation. Its native compiler path avoids GCC's internal `cp/` directory
shadowing the host `cp` command during `make install`.

```sh
python3 scripts/smoke-qemu.py --work .
python3 scripts/package-runtime.py \
  --baseline-rootfs /path/to/previous-verified-armel-rootfs \
  --builds builds --output packages/runtime
python3 scripts/prepare-rootfs.py \
  --source /path/to/previous-verified-armel-rootfs \
  --runtime packages/runtime --output rootfs --report evidence/rootfs.json
mksquashfs rootfs build/rootfs.squashfs -noappend -all-root \
  -comp zstd -Xcompression-level 22 -b 524288 -processors 4 -no-progress
```

The runtime manifest is pinned to the tested outputs. A differing rebuild
must be compared and validated before updating that pin; output hashes are
not promised to remain identical across changed build/toolchain paths.
The required next-candidate pipeline now applies this overlay after the
NVRAM fix, armel migration and four GCC 15 library builds. Its full output
matches the independently staged tree and the extracted SquashFS.

For full-system tests, use `prepare-guest.py` and `run-qemu.py` with the same
pinned #36 kernel, static BusyBox and previous usrmerge probes. Recompile
`identity-probe.c` with the ARM32 toolchain and replace only that test probe:
it now loads `libshared.so` by SONAME instead of requiring the removed flat
path. The remaining probes are unchanged; all input hashes are recorded.

## Validation and candidate

- All three libc smoke tests pass memory/allocator, pthread/TLS/mutex, libm,
  kernel calls, numeric resolver and staged gconv checks.
- In #36 Cortex-A53 QEMU, all **312 executable dependency checks pass with
  cache disabled**, and all 312 pass after the real ldconfig builds a cache.
  BusyBox executes before any cache is created.
- All three ABI probes, four rebuilt-library functional tests, 34 userspace
  command checks and module-path checks pass.
- Actual lighttpd configuration/module loading, iptables TCP extension loading
  and the strongSwan command path pass.
- ASUS executable identity checks pass. Finally the unchanged static init and
  metadata guard run as PID 1 with the cache removed; metadata-write rejection
  and non-inheritance across child exec both pass.
- The complete candidate preparation pipeline and unpacked SquashFS match the
  tested tree. The prepared source reproduces the pinned patched tree.

The first QEMU run exposed an obsolete absolute path in the **identity test
probe**, after all loader checks and plugin checks had passed. Updating the
probe to SONAME lookup made the full rerun pass; no extra compatibility link
was added to hide the harness dependency. The initial native staged install
also exposed the compiler-build `cp/` PATH collision described above; the
corrected install completed. Both failures are retained in local evidence.

`GT-BE98_leon36-ubuntu-multiarch_zstd22.pkgtb` is **88,333,388 bytes**, SHA-256
`67f896ed532531a345805dc14303b23b203d4545fb8cb11a5ab5df12d8c7a23d`.
The rootfs is 75,915,264 bytes, zstd-22 with 512 KiB blocks. The signed #36
bootfs is preserved bytewise and its signature verifies. No bootloader payload
is selected. Against the last measured replaceable-slot capacity of 734 UBI
blocks, reservations are 107+607, leaving 20 blocks. Capacity/slot state must
be read again before deployment. No flash, reboot or firmware commit was
performed for this checkpoint; QEMU does not qualify board services or Runner
throughput for these new glibc binaries.

References: [Ubuntu multiarch specification](https://wiki.ubuntu.com/MultiarchSpec),
[Ubuntu armhf libc6 layout](https://packages.ubuntu.com/resolute/armhf/libc6/filelist),
[Ubuntu glibc source package](https://packages.ubuntu.com/source/resolute/glibc).
