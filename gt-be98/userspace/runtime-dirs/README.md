# GT-BE98 runtime directory compatibility

2026-09-15. Extension of the validated merged-/usr candidate at commit
`94dccfe7d0954b4c5fe989efa8412a8d06dd5b13`, now verified in a hardware trial.

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
changes. The subsequent, explicitly requested hardware flash is described below.

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
hardware startup sequence. The subsequent hardware observations below cover
service startup and actual acceleration activity, not a throughput benchmark.

The candidate is 75,788,288 bytes (72.28 MiB), zstd 22, 512 KiB blocks:
the same rounded SquashFS size as the preceding usrmerge image. Its rootfs
reservation remains 606 UBI blocks. The rootfs component was subsequently
packed into an 88,206,412-byte PKGTB (84.12 MiB), preserving the signed #36
bootfs and every other original payload bytewise. The bootfs signature was
verified with the existing public key; no private key or re-signing was needed.

## Hardware trial and current rollback state

The router first returned to committed #35 in slot 2. The native inactive-slot
flasher then wrote the new image to slot 1 after checks of the model, booted
slot, both commit flags, fallback/loader hashes, image hash and fresh capacity.
Readback verified the new rootfs and unchanged fallback/physical loader before
selecting PART1_ONCE (6). No firmware commit was performed.

Current state: **slot 1 runs the new layout on kernel #36; slot 1 commit=0,
slot 2 commit=1; a normal reboot returns to #35 in slot 2**. Metadata sequences
remain 47/46. This is a trial, not a confirmed default image. Never run an
inactive-slot flasher while booted here: it would target the #35 fallback.

The five-minute boot logger ended normally at 306.783 seconds. No recorded
kernel faults; taint stays 4097 (existing P+O). PID 1 is `/usr/sbin/rc`, the
existing metadata guard is loaded only where intended, HTTP returns 200,
SSH/watchdog are running and all four Wi-Fi interfaces report up. The runtime
PID/socket and all three ABI probes passed on the physical router.

Docker was restored to its pre-flash running state without adding autostart.
Its client works through `/run/docker.sock`; memory/swap limits remain enabled.
A cached hello-world container passed with network disabled, 32 MiB memory,
32 MiB combined memory+swap and pids=32; no test containers remain.

Runner reports enabled L2/L3 hardware acceleration. Over 20 seconds, aggregate
L2 hardware hits rose 244079 -> 251583 and bytes 81974296 -> 85215844, with
zero runner flow/command errors. Flow ageing means these sums are not exact
traffic-rate measurements. No full-rate throughput test was performed.

The preexisting OpenVPN server did not automatically return during this boot.
`service start_vpnserver1` restored `tun21` and server state 2, errno 0, without
changing configuration. After that restoration, normalized IPv4/IPv6 firewall
hashes, forwarding sysctls and every interface's bridge/master relation match
the pre-flash baseline. Future VPN autostart behavior was not changed here.

See `flash/evidence/live-summary.json`, `flash/evidence/readback.txt`, and
`flash/evidence/network-comparison-final.json`. `flash/scripts` records the
guarded procedure used for this exact transition. Its state/hash checks are
intentionally specific; it is not a command to repeat blindly on the current
slot layout. Complete firmware and raw evidence are backed up on ML350.

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
