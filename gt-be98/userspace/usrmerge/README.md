# GT-BE98 merged-/usr candidate

2026-09-15. Completed offline on the DGX AArch64 host. No router files,
network settings, boot slots, or commit flags were changed.

## Result and Ubuntu alignment

The candidate uses the exact aliases shipped by Ubuntu 26.04 arm64
`base-files` 14ubuntu6:

```
/bin  -> usr/bin
/sbin -> usr/sbin
/lib  -> usr/lib
```

The Ubuntu package was downloaded and extracted for inspection only. Its
`preinst` rejects an unmerged filesystem and tells the installer to run
usrmerge first; it is not the conversion tool. Installing it wholesale would
also replace distribution identity and introduce dpkg/systemd/MOTD assumptions.
ASUS configuration in `/rom/etc`, writable `/etc -> tmp/etc`, `/opt`,
`/usr/local/share -> /tmp/share`, and ASUS init are preserved. This is still
ASUS/Leon firmware, not an Ubuntu installation. `/usr/sbin` remains a directory,
as in this specific Ubuntu package; no sbin-to-bin consolidation is implied.

References: [official package](https://packages.ubuntu.com/resolute/base-files),
[official source](https://archive.ubuntu.com/ubuntu/pool/main/b/base-files/base-files_14ubuntu6.tar.xz).
Downloaded package and source hashes match official repository metadata;
see `evidence/ubuntu-base-files.json`.

Runtime locations after the merge:

| ABI | Real directory | Preserved interpreter entry |
| --- | --- | --- |
| AArch64 | `/usr/lib/aarch64-linux-gnu` | `/lib/ld-linux-aarch64.so.1` |
| ARM hard-float | `/usr/lib/arm-linux-gnueabihf` | `/lib/ld-linux-armhf.so.3` |
| ARM soft-float ABI | `/usr/lib` | `/lib/ld-linux.so.3` |

Moving the flat ARM soft-float libraries into `arm-linux-gnueabi` is a separate
multiarch migration. It is not required to complete merged-/usr. The separately
rebuilt B53 glibc 2.44 archive is not overlaid here: this candidate retains the
glibc 2.44 set from tested firmware #36 to isolate the pathname change.

## Conflicts and preservation

The source is extracted from the hash-pinned #36 SquashFS, not from a mutable
router root. `merge-rootfs.py` copies to a new output and rejects unknown
collisions before copying. It resolves symlinks within the image, including
absolute links, without following them into the build host.

Four reviewed collisions:

- `/bin/bash` already targets `/usr/bin/bash`; keep the real executable.
- `libnmpapi.so` and `libws.so` copies are byte- and mode-identical; coalesce them.
- `/usr/lib/libresolv.so.2` is an older shadow copy. Keep the `/lib` copy that
  belongs to the active glibc 2.44 set, including its mode. Both input hashes
  are required by `scripts/resolv-policy.json`; the original image is retained.

Relocate `/lib/libexpat.so -> ../usr/lib/libexpat.so.1` to
`/usr/lib/libexpat.so -> libexpat.so.1`. Retaining its original relative target
would incorrectly refer to `/usr/usr/lib`.

All 3,478 other original regular-file paths retain their content and mode.
Existing symlinks that resolved to files still resolve to the same content.
All 182 module files, including the Broadcom/Realtek drivers, retain their
hashes. Directory modes are preserved. The original source remains unchanged.
See `evidence/preservation.json`; the full before/after inventory is in the
ML350 backup, not duplicated as a large Git text blob.

## Validation and limits

- Six conversion tests pass: reviewed collision/relative-link handling,
  unknown collision rejection, pinned library rejection, no output overwrite,
  absolute links confined to the image, and symlink-loop rejection.
- The actual resulting SquashFS was extracted and compared with the staged
  tree: every file, mode and symlink matches.
- Offline QEMU uses the actual #36 kernel, Cortex-A53, no NIC, no passthrough,
  and the candidate SquashFS mounted read-only.
- All 312 dynamically linked executables pass their own interpreter's `--list`.
  This validates dependency resolution, not full execution of every service.
- 34 userspace commands pass, including GNU tools, BusyBox, shells, SSH version,
  Btrfs tools, ebtables and disposable guest network-interface operations.
- AArch64, armel and armhf probes execute via their normal ELF interpreter;
  glibc 2.44, allocation, pthread/TLS, libm and numeric resolver checks pass.
- The unchanged ASUS `invalid_program_check()` accepts the canonical
  `/usr/sbin/rc` path with and without the existing preload guard.
- The unchanged init wrapper is exercised as guest PID 1, with a test rc and
  metadata provider: reads forward, automatic writes remain blocked, and child
  exec does not inherit the guard. No actual flash/metadata provider is used.
- `raid6_pq`, `xor` and Btrfs modules load through both directory aliases.

QEMU does not provide the router's Runner/DHD hardware. Full ASUS startup,
real forwarding acceleration and throughput still require a hardware trial.
No flashable PKGTB or flash operation is performed by these scripts.

The candidate SquashFS is **75,788,288 bytes (72.28 MiB)**, zstd level **22**,
512 KiB blocks, root ownership. It is 94,208 bytes larger than the old SquashFS
because directory ordering and compression grouping changed. With the native
flasher's 1 MiB reservation and 126,976-byte logical eraseblocks it needs
**606 rootfs blocks**, versus 605 for #36. Fresh slot/capacity checks are
required before a later flash; historical free-block counts are not sufficient.

## Reproduction

Run the transformation only after ASUS `buildFS` and all userspace overlays,
and before SquashFS creation. Running legacy installers after this step can
recreate directory conflicts. The rootfs has no separate early `/usr` mount;
all three aliases and their targets belong to the same SquashFS image.

Use the exact original rootfs and kernel hashes in `evidence/artifacts.json`.
The files are included in the ML350 artifact backup. Example from this folder:

```sh
unsquashfs -d source-rootfs /path/to/base36-rootfs.squashfs
python3 scripts/test-merge.py
python3 scripts/merge-rootfs.py --source source-rootfs --output rootfs \
  --resolv-policy scripts/resolv-policy.json --report evidence/merge.json
mkdir -p build
mksquashfs rootfs build/rootfs.squashfs -noappend -all-root \
  -comp zstd -Xcompression-level 22 -b 524288 -processors 4 -no-progress
```

Native probe build prerequisites are the separately published
[am-toolchains-aarch64 v2021.02.4-1 SDKs](https://github.com/leonpano2006/am-toolchains-aarch64/releases/tag/v2021.02.4-1)
(GCC 10.3, soft-float ARM and AArch64), plus the native AArch64 Ubuntu ARMHF
GCC 13.3 sysroot already pinned by `../glibc244-b53/evidence/arm32-toolchain-packages.json`.
The SDKs are external dependencies, not copied into this repository.
Host tools: Python 3 with pyelftools, QEMU system AArch64, squashfs-tools with
zstd support. No compiler runs on the router or ML350.

```sh
python3 scripts/build-probes.py --arm32-sdk /path/to/arm32-sdk \
  --arm64-sdk /path/to/arm64-sdk --armhf-ubuntu-sysroot /path/to/arm32-ubuntu \
  --output build/probes
python3 scripts/prepare-guest.py --busybox /path/to/static-aarch64-busybox \
  --probes build/probes --rootfs rootfs --squashfs build/rootfs.squashfs \
  --output build/guest.cpio.gz
python3 scripts/run-qemu.py --label usrmerge --kernel /path/to/Image36 \
  --initrd build/guest.cpio.gz --timeout 120 \
  --complete-marker QEMU_USRMERGE_COMPLETE
```

The BusyBox input hash is in `evidence/artifacts.json`. Guest probe sources,
the bootguard test double and all conversion/test scripts are included here.
Compiler output hashes are in `evidence/probes.json`.
