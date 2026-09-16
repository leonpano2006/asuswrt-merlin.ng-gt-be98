# GT-BE98 libgcc runtime update

This checkpoint prepares the next firmware candidate with the requested
`libgcc_s.so.1` versions. `libgcc-s1` is the Ubuntu package name.

| ABI | Previous | Candidate | Canonical directory |
| --- | --- | --- | --- |
| armel (soft float) | GCC 10.3.0 | Ubuntu GCC 15.2.0 | `/usr/lib/arm-linux-gnueabi` |
| armhf (hard float) | absent | Ubuntu GCC 15.2.0 | `/usr/lib/arm-linux-gnueabihf` |
| aarch64 | GCC 16.2.0 | existing GCC 16.2.0 retained | `/usr/lib/aarch64-linux-gnu` |

The 32-bit libraries are signed Ubuntu 25.10 (questing) cross-runtime packages
`15.2.0-4ubuntu4cross1`. The Ubuntu 26.04 GCC 15 compilers used in the preceding
checkpoint actually resolve their shared libgcc packages to a GCC 16 snapshot.
Copying that default runtime would not satisfy GCC 15. This recipe pins the
real GCC 15 packages, signed index, checksums and copyright files instead.
They are Ubuntu's generic ARMv5T soft-float and ARMv7/VFPv3-D16 hard-float
binaries, not newly rebuilt Cortex-A53 binaries. Both run on the router CPU.
The retained aarch64 library's `.comment` identifies GNU GCC 16.2.0; its hash
matches the prior firmware and live router.

Only two rootfs paths change: replace armel libgcc and add armhf libgcc. No new
flat aliases are added. All other files, glibc 2.44, libstdc++, init, rollback
guard, 182 kernel modules, vendor components and kernel #36 are preserved.
USB `/usr/local` and Docker remain external dependencies. Nothing is compiled
on the router and no compiler is installed there.

## Reproduce

Use an offline working directory on DGX, Python 3/pyelftools, Ubuntu archive
keyring, dpkg-deb, gpgv, squashfs-tools with zstd, OpenSSL, lzop and the
dependencies of [multiarch-loader](../multiarch-loader/README.md). Restore or
prepare that preceding rootfs; its inventory is pinned in runtime-policy.json.
Run these with new output paths (evidence directories can contain old reports):

```sh
python3 scripts/fetch-ubuntu.py
python3 scripts/stage-runtime.py --baseline ../multiarch-loader/rootfs --output packages/runtime
python3 scripts/prepare-rootfs.py \
  --source ../multiarch-loader/rootfs --runtime packages/runtime \
  --output rootfs --report build/reproduced-rootfs.json
python3 scripts/audit-abi.py --rootfs rootfs --baseline ../multiarch-loader/rootfs \
  --report build/reproduced-abi-imports.json
mksquashfs rootfs build/rootfs.squashfs -noappend -all-root \
  -comp zstd -Xcompression-level 22 -b 524288 -processors 4 -no-progress
```

Fetch verifies the saved signed InRelease, content-addressed indices and debs;
saved downloads from the backup also work offline. No host package is installed.
The manifest pins all three outputs, including the existing aarch64 file.
The [complete pipeline](../next-candidate/README.md) makes this overlay mandatory
after the NVRAM fix, armel migration, four library builds and multiarch glibc.
Its output matched the independent staging tree and unpacked SquashFS.
Fresh SquashFS timestamps may change its hash; inspect and validate new output
before updating the exact reviewed image pin in packaging-policy.json.

## Verification

See `evidence/verification.json`. All 1,172 old armel exports remain compatible;
the new runtime exports 1,177. Versioned libgcc imports in 69 existing consumers
and each new runtime's libc imports are satisfied by the matching glibc 2.44.

Full-system QEMU uses the exact #36 kernel on Cortex-A53, two CPUs and 1 GiB
RAM, with no NIC/host devices and the existing hardware-init exclusions. It
passes 312 dependency checks without cache, 312 with cache, three glibc ABI
probes, 34 userspace commands, the four prior library functional tests, legacy
plugin loading, merged-/usr identity and the PID1 metadata-write guard.

New tests exercise backtraces, wide signed division, pthread cancellation
cleanup, and C++ exceptions/RAII across a DSO on the main and worker threads.
They cover armel, armhf, aarch64 and a real legacy armel consumer compiled and
linked with GCC 10.3 and its old SDK, then run with the new runtime. All four
cases also pass on the physical router using explicit loader paths to copies
under `/tmp`. Logged provider paths and hashes identify the tested libraries.
Temporary probes were removed; installed libraries and boot metadata stayed
unchanged, and L2/L3 hardware acceleration remained enabled. Throughput was
not benchmarked in this runtime-only test.

Build probes with `scripts/build-probes.py --loader-checkpoint
../multiarch-loader --legacy-sdk /path/to/arm32-sdk`. Generated configuration
files from the preceding checkpoint provide Ubuntu GCC 15 toolchain paths.
AArch64 probes use host GCC 13.3 as a consumer of the existing GCC 16.2 runtime;
the runtime is not rebuilt or downgraded. The legacy SDK remains a separate
dependency. Use `prepare-guest.py` with the preceding saved busybox, probes and
library-probe, this SquashFS/rootfs and `--libgcc-probes tests/bin`, followed by
`run-qemu.py --label libgcc-runtime-v3 --kernel ../multiarch-loader/saved-inputs/Image36
--initrd build/guest-v3.cpio.gz --timeout 90 --complete-marker QEMU_USRMERGE_COMPLETE`.

Initial test harness runs lacked GCC's static `-lgcc` fallback and then loaded
two independent static C++ runtimes. Corrected test linking uses
`GROUP ( libgcc_s.so.1 -lgcc )`, DSO `-z defs` and executable `-rdynamic`.
Old and new runtime controls both failed before the last correction and both
passed afterward. Initial failures, controls and passing v3 logs are retained.
The candidate libraries did not change during these test corrections.

## Candidate and backup

`flash/GT-BE98_leon36-libgcc15_zstd22.pkgtb` is 88,370,252 bytes, SHA-256
`e1007e8210f357e1a6f7a3c8c899706644f953a84f05f5283859a948935460e0`.
Rootfs SHA-256 is `274ad17ea4c9878352a9648acfe8c4ce2057043b30068e0e410102df21fce3d6`.
Zstd level 22/512 KiB blocks add 36 KiB to the previous compressed rootfs.
The #36 bootfs and its verified signature remain unchanged; no bootloader
update is selected. UBI reservations remain 107+607 blocks, with 20 left in
the last read-only observation. Recheck capacity and slots before flashing.

The new complete image has not been flashed or hardware boot-tested. The
running prior multiarch image remains the uncommitted slot-1 trial, with
committed slot 2 / #35 as the normal reboot fallback. No firmware commit was
performed. Git contains code, test sources, policies, manifests, copyright and
reviewable evidence. Binaries, firmware and dependency archives are in the
private ML350 backup. The unchanged base, glibc builds and toolchain dependencies
remain in the preceding `multiarch-loader-backup.tar`, SHA-256
`5abd6984235c0e509b377b1e7b49496624a2d500491bb2d3399f81c255c9f31d`.
Local `completed.json` records the Git commit and verified backup receipt.
