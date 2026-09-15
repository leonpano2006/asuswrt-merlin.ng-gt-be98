# GT-BE98 armel multiarch and Ubuntu GCC 15 candidate

This checkpoint moves the existing 32-bit soft-float userspace libraries into
`/usr/lib/arm-linux-gnueabi` and rebuilds four shared libraries with Ubuntu
GCC 15.2, targeting B53 as Cortex-A53. It is integrated into
`../next-candidate/scripts/prepare-rootfs.py`. The SquashFS passed QEMU
validation with the exact #36 kernel, then was packaged and tested on the
physical GT-BE98. The new image is running as an uncommitted slot-1 trial;
normal reboot selects the committed #35 fallback in slot 2. See the
[hardware trial record](flash/README.md). No systemd change is included.

## Layout

| Purpose | Candidate location |
| --- | --- |
| armel shared libraries and private plugins | `/usr/lib/arm-linux-gnueabi` |
| armhf shared libraries | `/usr/lib/arm-linux-gnueabihf` (unchanged) |
| aarch64 shared libraries | `/usr/lib/aarch64-linux-gnu` (unchanged) |
| Old dynamic-loader ABI entries | `/lib/ld-linux.so.3`, `/lib/ld-linux-armhf.so.3`, `/lib/ld-linux-aarch64.so.1` |
| Kernel modules and shared data | Existing `/usr/lib/modules`, locale and package directories |
| Local additions on USB | `/usr/local`, with per-ABI library directories in loader configuration |

`/lib -> usr/lib` remains in place. The canonical armel directory contains
369 real ELF files, including private plugins/helpers. All 178 real armel
ELF files previously flat in `/usr/lib` have moved. The 289 relocated top-level
entries include SONAME aliases and the `ipsec`, `l2tp`, `libnl`, `netatalk`,
`pppd` and `xtables` directories. Old paths remain as compatibility links for
vendor consumers and hardcoded plugin paths. No real armel ELF remains flat.

One flat aarch64 library, `libebtc.so.0.0.0`, is deliberately preserved: its
bytes differ from the existing aarch64 multiarch version. This armel migration
does not silently merge different libraries with the same name.

Ubuntu also keeps ABI loader entry points outside triplet directories. Its
multiarch convention does not mean every directory under `/usr/lib` is an ABI.
See the [Ubuntu Multiarch specification](https://wiki.ubuntu.com/MultiarchSpec)
and [Ubuntu 26.04 arm64 libc6 file list](https://packages.ubuntu.com/resolute/arm64/libc6/filelist).
This is a firmware layout adaptation, not installation of an Ubuntu armel base.

`/rom/etc/ld.so.conf` includes `/etc/ld.so.conf.d/*.conf`; each ABI has a
fragment containing its `/usr/local/lib/<triplet>` and `/usr/lib/<triplet>`.
The generic local prefix and existing Entware/flat search paths remain in
separate compatibility fragments. ASUS init already links each `/rom/etc`
entry into writable `/etc` before running ldconfig; no init replacement is
needed for the new directory.

## Compiler and ABI

The compiler is the signed official Ubuntu 26.04 arm64-host
[`gcc-15-arm-linux-gnueabi`](https://packages.ubuntu.com/en/resolute/gcc-15-arm-linux-gnueabi)
cross compiler. Its 22 packages are extracted into a workspace prefix without
installing packages into the DGX host. The Ubuntu archive signature, index
hashes and every package hash are verified by `fetch-toolchain.py`.

Flags are `-O2 -fPIC -std=gnu11 -mcpu=cortex-a53 -mfpu=neon-fp-armv8
-mfloat-abi=softfp -U_TIME_BITS -U_FILE_OFFSET_BITS`. The last two options
override Ubuntu GCC 15's time64/file-offset64 defaults to preserve the legacy
armel ABI. This keeps 32-bit pointers, time_t and off_t for these libraries.
The Ubuntu cross sysroot's glibc 2.43 is a build input only; the firmware's
existing glibc 2.44 remains unchanged. The unrelated local GB10-tuned GCC 16
is not used.

| Rebuilt library | Existing version retained | SONAME | Exported symbols preserved |
| --- | --- | --- | --- |
| zlib | 1.2.12 | libz.so.1 | 102 |
| Expat | 2.0.1 | libexpat.so.1 | 80 |
| json-c | 0.12.1 | libjson-c.so.2 | 100 |
| libcap-ng | 0.8.4 | libcap-ng.so.0 | 22 |

`apply-libraries.py` checks original hashes, ARM ELF/float ABI, SONAME,
exported symbol names, versions, visibility, binding and object sizes before
writing any library. Package versions are intentionally unchanged in this
compiler migration. json-c's two calloc argument orders and intentional
fall-through comments are fixed in actual repository source and in an
idempotent, hash-guarded patch. The libcap-ng build regenerates the omitted
NEWS documentation placeholder only in its disposable build copy.

This is the first compiler-upgrade batch, not a claim that all proprietary
or legacy components now use GCC 15. BusyBox and armel/armhf glibc already
carried Ubuntu GCC 15.2; many existing added utilities already carried GCC 16.2.
The ELF inventory records compiler comments for the remaining components.
Kernel modules, Broadcom acceleration code and the other ABI libraries retain
their previous bytes.

## Reproduction

Use an aarch64 Linux host with Python 3, pyelftools, make, autoconf, automake,
libtool, patch, dpkg-deb, gpgv, Ubuntu archive keys, and squashfs-tools with zstd.
QEMU validation additionally requires qemu-system-aarch64 and the pinned
kernel, static BusyBox and probe inputs in `manifest.json`.

From this checkpoint directory in the firmware repository:

```sh
python3 scripts/fetch-toolchain.py --cache downloads --output toolchain
python3 scripts/build-libraries.py \
  --router-sources ../../../release/src/router \
  --toolchain toolchain --output build/libraries
python3 ../next-candidate/scripts/prepare-rootfs.py \
  --base-squashfs /path/to/verified-runtime-dirs-rootfs.squashfs \
  --patch-script ../webui-nvram-cache/scripts/patch-nvram.py \
  --rebuilt build/libraries/rebuilt --output rootfs \
  --report evidence/integrated-candidate.json
mksquashfs rootfs build/rootfs.squashfs -noappend -all-root \
  -comp zstd -Xcompression-level 22 -b 524288 -processors 4 -no-progress
python3 scripts/build-probe.py --toolchain toolchain \
  --build build/libraries --output build/library-probe
python3 scripts/prepare-guest.py --busybox /path/to/busybox-static \
  --probes /path/to/usrmerge-probes --rootfs rootfs \
  --squashfs build/rootfs.squashfs --library-probe build/library-probe \
  --output build/guest.cpio.gz
python3 scripts/run-qemu.py --label armel-multiarch --kernel /path/to/Image36 \
  --initrd build/guest.cpio.gz --timeout 60 \
  --complete-marker QEMU_USRMERGE_COMPLETE
```

The candidate wrapper pins the tested four output hashes; a differing rebuild
requires investigation and validation before updating that policy. Builds
from the clean Git source archive reproduced all four tested files bytewise.
The package cache and source archive are also backed up on ML350 because
rolling Ubuntu mirrors can eventually replace pinned versions.

Install paths are explicit: prefix `/usr`, libdir `/usr/lib/arm-linux-gnueabi`.
Only the selected library artifacts are copied into a new offline rootfs.
A generic upstream `make install` does not automatically infer this firmware's
multiarch policy. Local USB packages should instead set prefix `/usr/local`
and the applicable `/usr/local/lib/<triplet>` explicitly when supported.

## Validation and hardware trial

The exact #36 kernel, emulated Cortex-A53 and read-only candidate SquashFS
passed 312 dynamic-executable dependency checks, 34 userspace command checks,
all three ABI probes, four library functional tests, module-path tests and
the existing init identity/metadata-write guard tests. The library probe
verifies compression and gzip offsets, incremental UTF-8 XML parsing, JSON
int64/array/hash behavior, and in-memory capability operations. dladdr confirms
all four libraries load from the armel triplet directory.

The QEMU guest models ASUS's ROM-to-/etc symlinks and runs its actual ldconfig.
Board-only init calls are skipped on the virtual machine; no NIC, router
hardware or host block device is passed through. This does not validate Wi-Fi,
Runner throughput or complete ASUS service startup on the physical board.

The original source image is unchanged; 182 module files are identical.
4,169 original file/alias paths still resolve to identical bytes, ten paths
resolve to the four rebuilt libraries, and the two ld.so.conf aliases reflect
the intentional configuration change. The integrated recipe and extracted
SquashFS match the tested staging inventory. The new SquashFS is 75,804,672
bytes (16 KiB larger than its base), zstd level 22 with 512 KiB blocks.

The resulting PKGTB is 88,222,796 bytes. Its signed bootfs is bytewise
unchanged and its signature verifies. The inactive slot was written from
the #35 fallback; complete image readback passed before arming slot 1 once.
All 312 dependency checks, three ABI probes and four library functional
tests also passed on the physical router. Web UI login and live updates,
four radios, Docker DNS/HTTP/HTTPS and LAN port publishing worked. Runner
hardware counters increased without errors during observation; maximum
throughput was not benchmarked. All 88 loaded modules match the baseline.

The hardware trial preserves both the fallback bytes and its commit flag.
It does not commit the new firmware. The verified Docker networking and
USB `/usr/local` checkpoint remains an external runtime dependency. Systemd
remains a separate future init change. Detailed evidence, cold-boot network
differences and the guarded packaging/deployment scripts are in `flash/`.
