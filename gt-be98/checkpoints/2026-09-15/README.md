# GT-BE98 validated checkpoint — 2026-09-15

This checkpoint continues `gt-be98-102.7` at
`b4101d004fdf5eac0a4d3f94fd787786c167e0c7`. Existing Leon/Claude commits,
including the glibc 2.44 multiarch layers, GNU tools, AArch64 Dropbear and
SFTP, PSI, zswap/zsmalloc, and kernel zstd backports, remain in the history.
All firmware kernel builds described here ran on an AArch64 GB10 host.

| Image | Verified result | Boot status at 14:45 UTC |
|---|---|---|
| #34 initfix | Core cgroups, seccomp, services and Wi-Fi | Superseded |
| #35 | Btrfs POSIX ACL; Docker 29.8 on USB; active Runner hardware counters | Confirmed slot 2, fallback |
| #36 | Userspace memory and memory+swap accounting; Docker memory limits | Successful one-time slot 1 boot; **not confirmed** |

The Git commit records the work; it does not confirm a firmware slot.
At this checkpoint a normal reboot selects #35. #36 passed the tests below,
but its real-device observation was about six minutes, not a long stability
test. Do not infer full-speed forwarding performance from active counters.

## Contents and build scope

- The kernel source changes are integrated under
  `release/src-rt-5.04behnd.4916/kernel/linux-4.19`. They add opt-in
  `GTBE98_CGROUP_ABI` and `GTBE98_MEMCG_ABI` options with layout assertions.
- [kernel/README.md](kernel/README.md) contains the exact #35/#36 configs
  and the native build recipe. The normal SDK profile is not silently
  switched to the experimental configuration.
- [trial/README.md](trial/README.md) records the fixed init, metadata guard,
  FIT packing procedure, UBI sizing and one-time boot requirements.
- [docker/README.md](docker/README.md) contains the deployed daemon settings
  and private mount namespace helper.
- [gcc162-usb/README.md](gcc162-usb/README.md) records the GCC 16.2/glibc 2.44
  USB update, original deployment recipes and tests.
- [validation/](validation/) contains selected structured results, hashes
  and provenance. Local build paths in JSON are placeholders.

This is source, configuration and validation preservation, not a complete
clean-clone firmware distribution. The validated images were assembled from
the existing Leon #32 rootfs and SDK/prebuilt payloads. Private backups retain
those inputs and the #32/#35 rescue images. Generated objects, firmware
images, toolchain archives, credentials and raw device/network dumps are
not included here. A clean `make gt-be98` alone does not reproduce the USB
installation or automatically install the trial init wrapper.

## Validation boundary

Publication dependency verification started from the tracked source at the
base commit, then applied these kernel changes. Using the released SDKs
from `am-toolchains-aarch64`, it rebuilt Image, lib/crypto/Btrfs modules,
ARM32 init/boot guard and the AArch64 Docker helper. The newly built kernel
and modules passed the memory/controller and Docker OOM/swap QEMU tests.
See `validation/dependency-build.json` and `dependency-qemu-*.json`.
These rebuilt outputs were not flashed; the hardware results below refer
to the earlier #35/#36 image hashes. This does not establish a complete
firmware/rootfs build or bit-for-bit reproducibility of the prior images.

Core cgroups: pids (including hierarchy/fork/thread limits), devices,
freezer, cpuacct and seccomp filtering passed QEMU tests; pids and seccomp
also passed on the router. Btrfs ACL named-user access, mask and default
inheritance passed on hardware; ACL persistence after remount and zstd
roundtrip passed in QEMU.

For #36, 1,153 common header aggregates and 529 common vmlinux aggregates
were compared. Existing task/page members and bitfields retained their
positions; the three changed cgroup-internal structures were not part of
the original `CGROUPS=n` blob ABI. The 86-module QEMU matrix retained the
same 75 successful loads and 11 hardware-dependent failures, with no new
post-load memory/controller probe failures.

QEMU verified memory charging/freeing, cgroup OOM isolation, memory+swap
limits, 40 fork/exec/exit cycles and shared-mm owner transfer. Real Docker
in QEMU verified OOMKilled/exit 137 and swap-out/swap-in data integrity.
The guest swap device used a RAM-backed loop file. On hardware, a 32 MiB
memory/memsw container, pids limit 32, seccomp mode 2, 8 MiB filesystem write
and hello-world passed. Hardware OOM/swap stress was not performed.

The router retained HTTP/SSH/watchdog and all four wireless interfaces.
Runner reported Enabled, L2 & L3; observed L2 hardware hits increased from
125,528 to 141,512 over 20 seconds. Forwarding settings, firewall hashes
and interface masters matched before/after Docker. No new kernel faults
were observed; taint 4097 is the existing proprietary/out-of-tree P+O state.

CPU scheduling/quota, cpuset, blkio, slab accounting, rootless containers,
container networking, Podman and LXC remain outside this verified scope.
Future forwarding changes must preserve actual Runner hardware traffic.

## Test sources

`tests/` retains the probes used for this work. `memcgcheck.c`,
`basiccheck.c` and `pidscheck.c` are guest probes with their original paths;
prepare a disposable QEMU initramfs and its `/QEMU_LAB_GUEST` marker.
`docker-guest-init.sh` is an **initramfs PID 1 script**, not a host command.
It expects the modules, static Docker binaries, test image and Btrfs image
at the paths shown in the script. Its QEMU command and input hashes are in
`validation/qemu-docker-result.json`.

Live test scripts retain their deployment paths and version checks. They
are not generic diagnostics for arbitrary routers. No test is automatically
run by checking out this commit.
