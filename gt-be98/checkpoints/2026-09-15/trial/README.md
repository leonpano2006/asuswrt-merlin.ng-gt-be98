# Trial init, packaging and one-time boot

The original trial failed because it launched the ARM32 ASUS rc program
through `/lib/ld-linux.so.3 --preload ... /sbin/rc`. `/proc/self/exe` then
named the loader, causing ASUS `invalid_program_check()` to reject it.
`nvram_get_salt()` returned `(char *)-1`; a caller passed it to `strlcpy`,
and PID 1 died with SIGSEGV. A control image using the original #32 kernel
reproduced this. It was not a Btrfs or cgroup module-load failure.

`diag-init-fixed.c` uses normal `execve("/sbin/rc", ...)` and LD_PRELOAD.
The guard constructor clears LD_PRELOAD before rc main, retaining the
guard in PID 1 while subsequent execs do not inherit it. The five-minute
diagnostic logger writes only `/data/leon-trial-diag/boot.log`.
The guard forwards boot metadata reads and rejects automatic writes.
Manual native bootstate/commit tools run separately and remain usable.

The wrapper and shared guard use the ARM softfp-target SDK from
[am-toolchains-aarch64 v2021.02.4-1](https://github.com/leonpano2006/am-toolchains-aarch64/releases/tag/v2021.02.4-1),
pinned in [kernel/dependencies.json](../kernel/dependencies.json).
They are **ARM32 soft-float-ABI** binaries, matching
ASUS rc and `/lib/ld-linux.so.3`. Build `diag-init-fixed.c` as `/sbin/init`
and `bootguard-fixed.c` as the shared
`/usr/lib/leon-trial-bootguard.so` with the matching ARM32 SDK and `-ldl`.
The build command is:

```sh
python3 build-helpers.py --arm32-sdk /path/to/arm-softfp-sdk \
  --arm64-sdk /path/to/aarch64-sdk --output ../builds/trial-helpers
```

It compiles the init wrapper, shared guard and AArch64 Docker root-view
helper, and records their hashes. The output directory must be new.
`bootguard-fixed.c` includes the other two guard sources. The register
diagnostic code is intentionally ARM32-specific. Do not compile these
with the AArch64 USB GCC or replace `/sbin/rc` with the wrapper.

## Packaging

Preserve the Leon #32 userspace rootfs, then install the fixed init/guard,
the ebtables/libexpat SONAME fixes from `targets/buildFS`, the rebuilt
Btrfs module, ACL tools and the appropriate trial marker. #36 preserves
3,477 regular #35 rootfs files; only `btrfs.ko` and the marker changed.
ACL tool version and hashes are in the validation directory; their
AArch64 glibc requirements are satisfied by the existing 2.44 layer.

Create SquashFS from the prepared tree with the original ownership/modes:

```sh
mksquashfs rootfs rootfs.squashfs -noappend -comp zstd \
  -Xcompression-level 22 -b 524288
```

The bootloader's kernel FIT stays **LZO level 9**. This bootloader does not
support a zstd kernel payload. `fitlib.py` is the tested external-data FIT
parser/repacker; `pack-image.py` exposes explicit paths and capacity for
the same procedure. Supply the SDK's existing demo signing key locally;
no key is embedded in these tools. It verifies old/new RSA-PSS signatures,
all payload hashes and unchanged non-kernel boot components. Packing does
not write a router or set a boot commit flag.

```sh
python3 pack-image.py --original /path/to/known-good.pkgtb \
  --kernel /path/to/Image --rootfs /path/to/rootfs.squashfs \
  --key /path/to/SDK-demo-Krot-fld.pem \
  --available-blocks FRESH_CAPACITY --output /path/to/trial.pkgtb
```

`FRESH_CAPACITY` is a number obtained from the target immediately before
use: free UBI logical eraseblocks plus the inactive bootfs/rootfs blocks.
Use the actual logical eraseblock size (126,976 bytes on this device),
including the native flasher's extra 1 MiB reservation **per volume**.
No historical capacity observation is authorization to overwrite a slot.

| Image | Bytes | SHA-256 |
|---|---:|---|
| #35 | 88,068,896 | `dd805a4fea08b25383672c70cecb8f5318e9fc3099d06c06f7b8c6fe132b2f6b` |
| #36 | 88,112,204 | `a0455015bb848534987756857af53548bbcf726408bd902bf9345ef91a11684f` |

#36 required 107 + 605 logical eraseblocks; readback showed 22 free.
Rootfs compression level is a build input, not a level field readable from
the SquashFS superblock. The packer checks the codec and block size.

## Actual rollback behavior

The installed 2023 bootloader differs from the source-tree bootloader.
Observed one-time boots returned automatically to the committed slot after
the failed controls, without a manual power cycle. The old blanket claim
that BCM6813 cannot roll back was therefore wrong for this device and
procedure. This does not make every web flash or `hnd-write` a safe trial:
those paths may commit the image, defeating one-time fallback.

The verified procedure booted the committed good slot first, checked both
slot/loader hashes and capacity, used the native inactive-slot
`bcm_flasher` with a plain `.pkgtb` filename, verified written payloads and
unchanged fallback/loader, then separately selected PART2_ONCE (8) or
PART1_ONCE (6). The filename must not contain `linux.trx`, which selects a
different path in the vendor utility. A physical rescue image was available.

At this checkpoint #36 is running slot 1 while #35 is committed slot 2.
**An inactive-slot flash now targets the #35 fallback.** Return to the good
slot and recheck state before preparing another trial. This checkpoint
does not run a flasher, reboot, or confirmation automatically.
