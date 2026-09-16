# Cortex-A53 runtime candidate — 2026-09-16

All ten shared runtimes were rebuilt on the aarch64 DGX, against matching
**glibc 2.44** development sysroots. This includes `libgcc_s.so.1` and
`libstdc++.so.6` for armel, armhf and aarch64, plus the existing armel zlib,
Expat, json-c and libcap-ng versions. The glibc runtime itself is unchanged.

| ABI | Component | GCC | GNU SHA-1 Build ID |
| --- | --- | --- | --- |
| armel | libgcc | 15.2.0 | `e830f0e5032c76fa6f88ed8a0bae829c1448ef65` |
| armel | libstdcxx | 15.2.0 | `3b2f99f3b5d3e296c64820906756545cc0412c5e` |
| armhf | libgcc | 15.2.0 | `26ed9f8a5d08d99243c22701701b65e82281984c` |
| armhf | libstdcxx | 15.2.0 | `baaf0302a65af7bfbfd6a3e574d6bb4e050a6904` |
| aarch64 | libgcc | 16.2.0 | `376cad7a90099e3748af6df3f4c5dddb633210a3` |
| aarch64 | libstdcxx | 16.2.0 | `de00f61edc4f8aef2ce610a0ca9ec5b8055c32c0` |
| armel | zlib | 15.2.0 | `205aa2ab94e5655cade0b330eb3bb1efccea5e64` |
| armel | expat | 15.2.0 | `07667f395c2034bc07de31fcd62358619f18a771` |
| armel | json-c | 15.2.0 | `06d2e7085811bec09eb05e63988b793e50c1f107` |
| armel | libcap-ng | 15.2.0 | `500f79abf7977e9aa1b9c15b015626c2b4f4f651` |

Every stripped ELF retains its Build ID and `.GCC.command.line` section.
`packages/runtime-manifest.json` records SHA-256, source artifact hashes,
separate debug-file hashes, compiler versions and recorded CPU flags. GNU Build
IDs identify builds; they are not private-key authenticity signatures.

Aarch64 uses `-mcpu=cortex-a53+crc+crypto` literally. GCC's ARM32 port uses
`-mcpu=cortex-a53+crypto -march=armv8-a+crc+crypto
-mfpu=crypto-neon-fp-armv8`, with `-mfloat-abi=softfp` for armel and `hard` for
armhf. GCC 15 ARM does not accept the AArch64 spelling of the CPU extensions.
Preprocessor probes verify CRC/AES/SHA and ARM32 integer division. Disassembly
confirms `SDIV` and `UDIV` in both ARM32 libgcc division helpers. This is an ISA
check, not a throughput benchmark. Upstream assembly and runtime dispatch may
intentionally contain generic or separately guarded instructions.

## ABI and dependency checks

All old libgcc exports and all aarch64 libstdc++ exports remain compatible.
The GCC 10 armel libstdc++ had 11 weak inline/template instantiations absent
from upstream GCC 15. Their exact names, the 288 strong-to-weak changes and
the condition-variable wait default-version change are pinned in
`configs/armel-libstdcxx-abi-delta.json`. Existing condition-variable clients
retain their old versioned symbol; new clients use the newer default.
No ARMEL firmware ELF or literal lookup references the 11 removed symbols.
No object size, visibility or unreviewed ABI change is accepted.

The complete candidate passes 739 public versioned dependency checks,
including 70 libgcc consumers and both libstdc++ consumers (`libasusnatnl.so`
and `ftpclient`). This does not claim compatibility with an external plugin
that explicitly calls one of the removed internal exports. GCC's ABI policy
explains compiler-generated ABI leakage and versioned symbols:
https://gcc.gnu.org/onlinedocs/libstdc++/manual/abi.html

Full-system Cortex-A53 QEMU uses the exact #36 / 4.19.294 kernel. It passes
312 executable dependency checks without a cache and 312 with one; 34 userspace
commands; all three glibc ABI probes; legacy plugins; the four library functional
checks; and the PID1 metadata guard. New tests cover five compiler cases:
three current target compilers, original GCC 10.3 armel SDK clients, and GCC 13
aarch64 clients. All five pass backtraces, wide arithmetic, forced-unwind thread
cancellation and C++ exceptions/RAII across a DSO. Ten C++ tests exercise both
string ABIs, strings/streams/locale/regex/filesystem, threads, condition variables
and futures. Modern consumers link the newly built shared libstdc++ and libgcc;
legacy consumers link their original SDK and then execute with the new runtime.

The same five cases, ten dual-ABI tests and four C library checks pass on the
physical router through explicit loader paths under `/tmp`. Logged provider
paths prove the new runtimes were loaded. All 242 installed library hashes and
boot metadata are unchanged; L2/L3 hardware acceleration remains enabled.
Temporary test files were removed. See `evidence/verification.json` and the
retained QEMU/hardware logs.

## Build inputs and reconstruction

This checkpoint is an overlay, not a standalone firmware source tree. Restore
the existing DGX workspace inputs before rebuilding. `dependency-backups.json`
identifies the preceding ML350 archives and external compiler SDKs; the aarch64
Buildroot toolchain remains a separate project. GCC 15 source is the unmodified
15.2.0 upstream tarball inside the authenticated Ubuntu source package, not the
Ubuntu binary libgcc package. `verify-source-inputs.py` checks the signed
InRelease -> package-index -> source-package chain. GCC 16.2 source is pinned
to the archive used by the existing native compiler. Preserve the source
archives, compiler build, GNU licenses and provenance when redistributing.

The build scripts use the restored workspace layout (dated checkpoint sibling
directories). Generated `configs/build-targets.json` and compiler wrappers are
machine-local outputs; regenerate them after relocating the workspace. The
firmware overlay pipeline itself accepts explicit dependency paths and also
works with the short checkpoint directory names in this Git repository.

1. Restore `multiarch-loader-20260916/builds/{armel,armhf,aarch64}/stage`, Ubuntu
   ARM compiler directories, `github-push-20260915/dependency-sdks`, and the
   existing `gcc162-usb` source/native compiler build. Extract the pinned GCC 15
   source package and its `gcc-15.2.0.tar.xz` into `sources/`.
2. In a fresh checkpoint output directory run `scripts/prepare-sysroots.py`.
   It verifies glibc headers and target feature macros.
3. For each ABI run `scripts/build-libgcc.py ABI --jobs 4`, then
   `scripts/build-libstdcxx.py ABI --jobs 4`. ARM support headers come from the
   matching GCC make rules; target libraries use the Ubuntu GCC 15 compiler.
   C++ needs the normal sibling `../libgcc` build layout; configuration is
   rejected if threads are silently disabled. New libgcc paths precede old
   compiler paths, and link maps retain the actual glibc/libgcc inputs.
4. Run `scripts/build-c-libraries.py --router-sources PATH/release/src/router
   --armel-checkpoint ../armel-multiarch-20260915`. Source file hashes and the
   prior json-c GCC 15 compatibility patch are recorded. No C library version
   or ARM32 time/file-offset ABI is changed; static libgcc comes from this build.
5. Run `scripts/stage-runtimes.py` and `scripts/build-probes.py`. Staging checks
   CPU flags, SONAME/ABI changes, Build IDs and strip invariants. Outputs are
   newly created paths. A rebuild with different artifacts must be inspected
   and its manifest pins updated before it can pass the deployment gate.
6. Apply `scripts/prepare-rootfs.py --source BASE --runtime packages/runtime
   --output NEW_ROOT --report REPORT.json`, and run `audit-dependencies.py`.
   The [complete next-candidate pipeline](../next-candidate/README.md) makes
   this overlay mandatory after all previous validated changes.
7. Pack SquashFS with `-comp zstd -Xcompression-level 22 -b 524288 -all-root`.
   Use `prepare-guest.py` and `run-qemu.py` with the preceding saved QEMU inputs,
   then `pack-rootfs.py` only after reviewing its exact image/hash pins and
   freshly reading UBI capacity. The scripts never flash or commit firmware.

The full preparation pipeline, independent staging tree and unpacked SquashFS
have identical inventories. Only the ten runtime payloads and necessary
multiarch SONAME links change. Kernel #36, all 182 module files, vendor blobs,
merged-/usr layout, glibc, bootguard and previous Web UI fixes are preserved.
There are no new flat `/usr/lib` aliases. USB `/usr/local`, Docker and the ldd
entry repair remain the existing external runtime dependencies.

## Candidate artifact

`flash/GT-BE98_leon36-a53-runtimes_zstd22.pkgtb`: **89,439,308 bytes**.
SHA-256: `7d48c2274be8dae6179096208a738d5214b321805b6d1fa9f0736bf23eff92f9`.
Rootfs: 77,021,184 bytes, SHA-256
`68888e499d0095374266c8f2adf0be296c5370e893c81c548e7a36c1030e9216`.
The signed #36 bootfs is preserved bytewise and its signature verifies.
Current UBI arithmetic reserves 107 + 615 of 734 available replacement blocks,
leaving 12 eraseblocks; recheck before any flash.

**This image has now been flashed and verified as a full firmware on GT-BE98.**
Installed-runtime, multiarch, Web UI, Docker networking/memcg and hardware
acceleration checks passed; see [physical trial results](flash/README.md).
Slot 1 remains uncommitted, with committed slot 2 / #35 as the normal reboot
target. No firmware commit occurred.
