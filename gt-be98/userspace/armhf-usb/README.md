# External USB ARM hard-float runtime

2026-09-17. The candidate's entire `/usr/lib/arm-linux-gnueabihf` directory
is replaced with this symlink:

```
/usr/lib/arm-linux-gnueabihf
  -> /tmp/mnt/JFFS/system-libs/gt-be98/8da410f090d92cff/arm-linux-gnueabihf
```

The destination is directly under the existing USB Btrfs root, outside both
`/jffs_root` and `/jffs_root/usr-local`. It does not use `/usr/local` and adds
no mount or global library-search setting. Existing `/lib -> usr/lib` and
`/usr/lib/ld-linux-armhf.so.3 -> arm-linux-gnueabihf/ld-linux-armhf.so.3` stay intact.
The version directory is identified by a manifest hash, so a future runtime
update need not overwrite files used by another firmware version.

## Actual result

- Externalized 23 regular files and the existing relative libstdc++ symlink,
  totaling 4,963,844 uncompressed bytes. Source content and modes are retained.
- Starting with the full OpenSSL 4 -Oz/LTO candidate and packer zstd 1.5.7,
  rootfs shrinks from 80,953,344 to **79,257,600 bytes**: **1,695,744 bytes
  (1.617 MiB) saved**.
- The prior slot1 rootfs allowance is 78,565,376 bytes with the original
  reserves. This image remains **692,224 bytes / 676 KiB too large**.
- Tor, Ookla, iperf3, SQLite CLI, ARMEL and AArch64 runtimes all remain in
  internal rootfs. Only the requested ARMHF directory is externalized.
- Rootfs SHA256: `a8cec3e464d89aee4565c2149a097c2aff3a71dc9e036dfa1c75dab92665e048`.
- No flashable firmware package was produced, no flash/reboot/firmware commit
  occurred, and no rollback metadata or existing system libraries were changed.
  The versioned payload **has been installed and verified on the actual USB**.
  The live read-only `/usr/lib` still has its old directory until a future flash.

## Validation and operational boundaries

The firmware ELF audit finds ARMHF objects only inside that directory; there
are no other in-tree ARMHF executables. A live `/proc/*/maps` snapshot found no
ARMHF users. This does not inventory every third-party program on USB or prove
that a later configuration cannot start one.

With exact kernel #36 in offline QEMU, the packed directory link is tested
before and after an external-directory mount. Without USB, all 330 native/ARMEL
ELF interpreter and dependency checks pass with loader caches inhibited. After
mounting a tmpfs simulation of the USB directory, ARMHF glibc, libgcc unwinding,
thread cancellation, C++ DSO exception handling, and both libstdc++ string ABIs
pass, both without and with an ldconfig cache. After simulated unmount, ARMHF
launch correctly fails while native systemctl and ARMEL BusyBox still execute.
The test does not run Broadcom hardware initialization or simulate physical USB
timing. Do not unplug the USB while an ARMHF process is running.

On hardware, the new USB loader and libraries pass the same bounded runtime
and C++ probes using explicit paths. The existing global rc-notify preload
still comes from the unchanged live canonical path; full directory indirection
was exercised in QEMU. All original live ARMHF file hashes and bootstate remain
unchanged, and hardware flow acceleration reports enabled before and after.
This is not a network throughput benchmark or a boot test of new firmware.

The USB label/mountpoint `/tmp/mnt/JFFS` is now a prerequisite for ARMHF use.
It must be mounted before an ARMHF service starts. The ARM64 and ARMEL boot
runtimes remain internal. No new ARMHF service or startup dependency is added
in this change. The payload's own parent is created atomically from staging;
existing version directories are verified instead of overwritten.

## Replay / dependencies

This is out-of-tree work based on the `rootfs-slim-20260917` checkpoint
(candidate branch tip before this change: 8b6fb608c985269b0c59cc71ae4f3436d10c6aa2).
It also needs the userspace-refresh SDK, previous zstd 1.5.7 library, the
systemd-rc-next sort script, multiarch-loader inventory helpers and Image36,
and the a53-runtimes guest fixture. Those are saved in earlier checkpoints.

Create `build` and `evidence` directories in a fresh checkpoint, then run:

1. `scripts/audit.py`
2. `scripts/stage.py` (copies the reviewed parent, externalizes the directory,
   preserves the remaining inventory, and recompresses)
3. `scripts/test-qemu.py` (verifies unpacked contents and runs bounded VM tests)
4. `scripts/prepare-live.py` (creates root-owned USB tar and explicit-path probes)

The generated `build/live/install-test.sh` is hardware-specific and requires
GT-BE98, kernel 4.19.294, and the existing executable Btrfs USB mount. It only
adds this versioned USB payload and test files in a dedicated `/tmp` directory.
It never replaces the live `/usr/lib` directory, changes `/usr/local`, or flashes.
For repeat offline tests, use clean output paths rather than deleting previous
evidence. The measurement's `router_modified: false` describes compression only;
`result.json` records the later additive USB installation.
