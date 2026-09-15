# GT-BE98 runtime directory compatibility

2026-09-15. Offline extension of the validated merged-/usr candidate at
commit `94dccfe7d0954b4c5fe989efa8412a8d06dd5b13`.

Added paths:

```
/run -> var/run
/media                 root:root 0755, empty
/srv                   root:root 0755, empty
```

The live router has `/var` on tmpfs and `/var/run` owned by UID/GID 0 with
mode 0755. ASUS `rc/init.c` creates `/var/run` during early startup. This
compatibility link exposes that same existing volatile directory as `/run`.
It uses the reverse link direction from Ubuntu's usual `/var/run -> /run`,
so ASUS can keep ownership of directory creation and clearing at boot.
`/run` becomes available when ASUS creates `/var/run`; this does not provide
a new, independently mounted `/run` before that point in early init.

PID files and UNIX sockets opened through either name refer to the same
objects. The link does not add another tmpfs or reserve RAM. `/var/lock`
retains its current independent path and mode; `/run/lock` is not added.
`/media` and `/srv` are empty locations for future mounts/service data;
creating them does not configure automounting or make SquashFS writable.

This follows the transient-data purpose described by
[FHS /run](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch03s15.html).
It does not claim complete Ubuntu filesystem or init compatibility.

The transformation adds only these three entries. All 4,564 preexisting
entries retain their type, mode, file content and symlink target. No init,
glibc, kernel, module, mount configuration, forwarding or boot-commit code
changes. Router access was read-only inspection; no live installation or
flash was performed.

## Validation

The resulting read-only SquashFS was tested with the real #36 kernel in
offline Cortex-A53 QEMU:

- `/run` and `/var/run` have the same device/inode, tmpfs backing, UID/GID 0
  and mode 0755.
- A PID file created through `/run` is visible and removable through
  `/var/run`.
- A UNIX socket bound through `/run` accepts a connection through `/var/run`.
- Recreating the guest `/var` tmpfs clears a sentinel from the previous mount.
- `/media` and `/srv` have mode 0755.
- All 312 executable dependency checks and the three ABI probes pass.
- The 34 userspace commands, ASUS canonical-path identity check, module path
  checks and PID 1 metadata-write guard tests from merged-/usr pass.

The test mounts a disposable `/var` tmpfs and creates its initial directories
according to the source/live layout. It does not exercise the entire ASUS
hardware startup sequence. Runner/DHD function still requires a later real
hardware trial. No extra live safety or throughput claim is made.

The candidate is 75,788,288 bytes (72.28 MiB), zstd 22, 512 KiB blocks:
the same rounded SquashFS size as the preceding usrmerge image. Its rootfs
reservation remains 606 UBI blocks. This is a rootfs component, not a PKGTB
firmware file; a later trial needs fresh slot/capacity checks.

## Reproduction

Use the original merged-/usr input hash in `evidence/artifacts.json`.
From this folder:

```sh
python3 scripts/add-runtime-dirs.py --source /path/to/merged-rootfs \
  --output rootfs --report evidence/preservation.json
mkdir -p build
mksquashfs rootfs build/rootfs.squashfs -noappend -all-root \
  -comp zstd -Xcompression-level 22 -b 524288 -processors 4 -no-progress
/path/to/arm64-sdk/bin/aarch64-buildroot-linux-gnu-gcc \
  -O2 -Wall -Wextra -mcpu=cortex-a53 scripts/runtime-probe.c \
  -o build/runtime-probe
python3 scripts/prepare-guest.py --busybox /path/to/static-aarch64-busybox \
  --probes /path/to/usrmerge-probes --usrmerge-scripts ../usrmerge/scripts \
  --runtime-probe build/runtime-probe --rootfs rootfs \
  --squashfs build/rootfs.squashfs --output build/guest.cpio.gz
python3 ../usrmerge/scripts/run-qemu.py --label runtime-dirs \
  --kernel /path/to/Image36 --initrd build/guest.cpio.gz --timeout 120 \
  --complete-marker QEMU_USRMERGE_COMPLETE
```

Dependencies are the preceding `../usrmerge` source/probes and its pinned
kernel/static BusyBox, pyelftools, QEMU and squashfs-tools. The AArch64
compiler is the external am-toolchains-aarch64 v2021.02.4-1 GCC 10.3 SDK.
Compilation runs natively on DGX, not on the router or ML350.
