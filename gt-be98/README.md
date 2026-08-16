# GT-BE98 — Asuswrt-Merlin build notes and patches

Patches and build tooling for the **ASUS GT-BE98** (non-Pro) on top of the
[gnuton fork](https://github.com/gnuton/asuswrt-merlin.ng) of Asuswrt-Merlin.

Branch base: tag **`3006.102.6_1-gnuton1`**
Hardware: BCM6813 (HND 5.04 BE SDK, profile `96813GW`), quad Brahma-B53 ARMv8,
2 GB RAM, **Linux 4.19.294**.

Everything here was developed and verified on real hardware, except where
explicitly marked otherwise.

---

## What's in the branch

`gt-be98-102.7` (the default branch) is based on gnuton's `DEV_3006.102.7_2`
and carries nineteen self-contained commits.  Most are not GT-BE98-specific
and should apply to any HND 5.04 BE / 4916 target.

**Original series** (from the 102.6 era, cherry-picked forward):

| Commit | What | Notes |
|---|---|---|
| `usb: detect and mount btrfs and xfs USB partitions` | Makes btrfs/XFS sticks automount | Verified on hardware |
| `build: expose the kernel's own menuconfig` | `make kernel-config-prep` / `kernel-menuconfig` | Tooling only |
| `nfs: build nfs-utils and portmap against libtirpc` | Fixes NFS under glibc 2.32 | Compiles; portmap change **not runtime-tested** |
| `buildFS: install the aarch64 glibc layer and GNU coreutils` | 64-bit userland layer | Inert without the `fs.src` payload |
| `kernel: GT-BE98 config` | btrfs, XFS, zram/zswap, WireGuard, overlayfs, namespaces | Opinionated |
| `GT-BE98: local build settings` | ROG UI on, NFS off, build tag | **Drop this one when rebasing** |

**102.7-era additions:**

| Commit | What | Notes |
|---|---|---|
| `kernel: enable madvise/fadvise syscalls and JFFS2 xattrs` | Broadcom disables `ADVISE_SYSCALLS`; that also kills THP (madvise mode has no entry point) and allocator memory release | Verified: THP works end-to-end after this |
| `build: give mtd-utils-install the stage include/lib paths` | Upstream bug: any **clean-tree** build dies at install-time recompile of `mkfs.ubifs` | Bites every fresh clone |
| `kernel: expose zswap stats in /proc/meminfo` | Backport of 5.19 `f6498b776d28` (minimal: no vmstat half) | htop's zswap display works on 4.19 |
| `zswap: default to zstd compressor and z3fold zpool` | Kernel defaults match what boot scripts set by hand | |
| `lib/zstd: upgrade to zstd 1.5.2` | Kernel zstd 1.3.1 → 1.5.2 (from linux 6.6 LTS) + all three callers ported | zswap/btrfs/squashfs hot paths |
| `sched/psi: backport pressure stall information` | `/proc/pressure/{cpu,memory,io}` on 4.19 — see *Backports* below for the blob-safety technique | Verified live |
| `build: strip stray core dumps from the www rootfs` | A crashing build helper shipped 48 MB cores **inside the firmware image** | See gotchas |
| `userland: ship 64-bit nano 8.6 and iperf3 3.19` | Replaces the 32-bit in-tree builds | See *64-bit layer* below |
| `buildFS: retire /lib64; teach ld.so.conf the multiarch dirs` | Full Debian-multiarch layout — `ldd` shows `/lib/aarch64-linux-gnu/...` | The vendor's only /lib64 consumer (ebtables) is long since replaced |
| `mm/zswap: backport the 6.5 pool shrinking mechanism` | zswap keeps its own LRU; **zsmalloc gains writeback** and becomes the default zpool | Hand-port of f999f38b4e6f; see *Backports* |

To rebase onto a newer upstream branch/tag:

```sh
git fetch origin <new-branch-or-tag>
git rebase --onto <new> <old-base> gt-be98-102.7
```

---

## Building

The gnuton toolchain image keeps its toolchains in
`/home/docker/am-toolchains/brcm-arm-hnd`, but `platform.mak` hardcodes
`/opt/toolchains`. `amng.sh` symlinks it on entry and runs everything inside the
container.

```sh
# optional: ccache spliced in front of the two 4916 toolchains (~60 GB cache)
docker build -t amng-toolchains:ccache -f gt-be98/Dockerfile.ccache .

gt-be98/amng.sh make PARALLEL_BUILD=-j$(nproc) gt-be98    # build
gt-be98/amng.sh                                           # interactive shell
```

> ### Never pass `-j` at the top level
>
> `make -j88 gt-be98` races on the shared staging directory. It does not fail
> cleanly — it produces **silently poisoned autoconf caches** (a package caches
> "no stdlib.h" and then dies much later with implicit-declaration errors) and
> corrupt `.o` files that surface as a BFD internal error during the vmlinux
> link. `PARALLEL_BUILD=-jN` is consumed only by the kernel build and is never
> defined in-tree, so it is the safe knob. gnuton's CI runs plain `make gt-be98`
> fully serial, which is why upstream never hits this.
>
> Recovery from a poisoned tree is `git clean -xfd` plus a full rebuild. An
> *interrupted* build, by contrast, is self-healing — just resume it.

Build output is a `.pkgtb` under `release/src-rt-5.04behnd.4916/targets/`.

---

## Kernel configuration

`make menuconfig` in the SDK is Broadcom's **profile** menuconfig, not the
kernel's. And running `make menuconfig` inside `kernel/linux-4.19` by hand is
worse than useless: without the SDK environment kconfig silently drops ~190
`CONFIG_BCM_*` symbols — the entire platform — and the result will not boot.

`kconfig.sh` routes through the `kernel-menuconfig` target added in this branch,
which keeps that environment:

```sh
gt-be98/kconfig.sh menu     # normalise, snapshot a baseline, open menuconfig, save
gt-be98/kconfig.sh diff     # your deltas vs the normalised upstream config
gt-be98/kconfig.sh save     # .config -> config_base.6a.6813
gt-be98/kconfig.sh apply    # replay the saved fragment (after a git checkout wiped it)
gt-be98/kconfig.sh reset    # restore config_base.6a.6813 from git
```

The baseline is the *normalised* config rather than raw git, because the build's
`olddefconfig` pass collapses duplicate lines and drops prompt-less symbols —
diffing against git would bury your edits in that noise.

> ### Do not enable `CONFIG_CGROUPS` (or anything that changes core struct layout)
>
> It bricks the boot, and **there is no automatic rollback** (see below).
>
> This SDK links **114 prebuilt binary Broadcom kernel objects** — `dhd.o`
> (wifi), `pktrunner.o` (accel), `bcm_enet.o` (ethernet), `bdmf.o`, `hnd.o`,
> `emf.o`, `igs.o`, `bcm_mpm.o` — all compiled by Broadcom against a
> `CGROUPS=n` kernel. Enabling `CGROUPS`/`MEMCG` changes the layout of
> `struct page` and `struct task_struct`, so those blobs read the wrong offsets
> and panic before console output. The entire datapath (NIC → accelerator →
> wifi) is binary-only, so **Docker and containers are permanently impossible
> on this box.**
>
> Namespaces (`NET_NS`, `PID_NS`, `IPC_NS`, `UTS_NS`) are fine — they don't
> touch those structures — and are enabled in this branch.

---

## Flashing

```sh
hnd-write /path/to/image.pkgtb && reboot
```

* **Exit code 99 means success** — the write completed and the new slot is
  committed. It is not an error.
* **Exit code 5 (EIO) almost always means out of UBI space.** Image slots are
  dynamic UBI volumes, so a flash needs
  `avail_eraseblocks + victim-slot EBs >= required`. The real error text goes
  only to the serial console; you can recover it by running `hnd-write` under
  Entware's `strace` and reading the `write()`s to `/dev/console`. The fix is to
  shrink the `jffs2` UBI volume (back it up first — on Broadcom it is *not*
  auto-recreated; that rc code is MTK-only).

> ### BCM6813 has NO automatic rollback of any kind
>
> The dual image is a **manual A/B switch**, not a self-healing one. Verified in
> the U-Boot source, three independent reasons:
>
> 1. **The fallback code is compiled out.**
>    `CONFIG_BCM_BOOTSTATE_FALLBACK_SUPPORT` is `default n` and appears only in
>    the `963178/963158/963138/94912` defconfigs. `bcm96813_defconfig` has only
>    `CONFIG_BCM_BOOTSTATE=y`, so `check_image_fallback_needed()` is absent from
>    the BE98's TPL and image selection degenerates to
>    `selected_img_idx = committed`, forever.
> 2. **Even where it exists it is not a "three strikes" counter.** There is no
>    counter anywhere in that code. It is a one-shot "did the last boot reach
>    steady state" test that requires a watchdog-tagged software reset. An early
>    kernel panic followed by a power cycle does not produce one.
> 3. **`try_another` only retries the other slot when the image fails to
>    *load*** — bad UBI volume, or missing FIT magic. A structurally valid image
>    whose kernel panics later never engages it.
>
> The only in-band switch is `bcm_bootstate 2` (`BOOT_SET_OLD_IMAGE`), which
> needs a *running* system and is therefore useless when bricked. Recovery is
> always physical **rescue mode**: unplug, hold the reset pinhole, plug in while
> holding ~10 s until the power LED blinks slowly, then TFTP a known-good
> `.pkgtb`. Keep one on hand before you flash anything experimental.
>
> Note the BE98 has exactly **one 1 Gbps port** (the rest are 2.5G/10G); U-Boot
> likely brings up only that PHY, so use it for the TFTP recovery.

**Verify a flash by fingerprint, not by version string.** A local build leaves
`EXTENDNO=0`, so consecutive self-builds are indistinguishable in the web UI.
Use `uname -a` (build number `#N` and timestamp) or a feature marker. Also note
the build container runs **UTC** while your host may not — `compile.h` reading a
couple of hours behind `vmlinux`'s mtime is a timezone gap, not a stale kernel.

---

## Using btrfs and XFS on a 4.19 kernel

Modern mkfs tools default to on-disk features 4.19 cannot mount.

**btrfs — exactly one blocker:**

```sh
mkfs.btrfs -O ^block-group-tree /dev/sdXN
```

`block-group-tree` (the default since btrfs-progs 6.19) needs Linux 6.1+.
Without `^bgt` the mount fails with a bare `open_ctree failed` and *no*
"unsupported optional features" line in dmesg. `free-space-tree`, `extref`,
`skinny-metadata` and `no-holes` are all fine.

**XFS — fussier:**

```sh
mkfs.xfs -m crc=1,bigtime=0,inobtcount=0,metadir=0,reflink=1,rmapbt=1 \
         -i nrext64=0,exchange=0 -n parent=0 /dev/sdXN
```

`reflink` and `rmapbt` *are* supported on 4.19; the rest are later inventions.

**Compression is a subvolume property, not a mount option** — ASUS's automount
cannot pass mount options:

```sh
btrfs property set /tmp/mnt/LABEL compression zstd
```

Two 4.19 traps here:

* `compress=zstd:3` as a mount option fails `EINVAL` — the `:level` suffix is a
  Linux 5.1 feature. Use plain `compress=zstd`.
* A level suffix in the *property* xattr is **silently ignored**:
  `btrfs_compress_is_valid_type()` compares only the first four characters. If
  you want high-ratio compression, do it once offline with
  `btrfs fi defrag -r -czstd -L 15` (the level flag is `-L`; `-czstd:15` is
  rejected outright) and let the router's own writes fall back to level 3.

Also: btrfs cannot host a swapfile on 4.19 (swapfile-on-btrfs landed in 5.0) —
use a separate swap partition.

---

## Router-side scripts

`router/` holds the two files that live on the router itself, not in the
firmware image.

* **`post-mount`** — Merlin calls it with the mounted path as `$1`. Binds a USB
  partition over `/jffs`, restores the Entware link, and arms zswap plus swap.
  Edit `SWAP_UUID` first (`blkid` to find yours).

  Two things worth knowing: at boot this runs from the *underlying* ubifs
  `/jffs`, not the USB copy, so **keep both copies identical**. To reach the
  ubifs copy once the bind is in place:
  `mount -t ubifs ubi:jffs2 /tmp/realjffs`. And busybox `swapon` has no
  `-U`/`-L` and there is no `/dev/disk/by-uuid`, hence the `blkid` lookup.

* **`inputrc`** — copy to `/root/.inputrc`. A bash built here is not linked
  against ncurses, so readline cannot read `kdch1`/`kich1`/`kpp`/`knp` from
  terminfo and Delete simply does nothing. These four bindings restore it.
  (Entware's bash is linked against ncurses, which is why it behaves.)

---

## Gotchas index

| Symptom | Cause |
|---|---|
| Build dies with configure-detection nonsense, or BFD internal error | Top-level `-j`. Poisoned tree — `git clean -xfd` and rebuild |
| `make menuconfig` loses all `CONFIG_BCM_*` | Ran it outside the SDK environment. Use `kconfig.sh` |
| Kernel panics before console output | Something changed `struct page` / `struct task_struct`. Almost always `CGROUPS` |
| `hnd-write` returns 99 | Success |
| `hnd-write` returns 5 | Out of UBI space; shrink the jffs2 volume |
| Flashed image "didn't take" | `EXTENDNO=0` — check `uname -a`, not the version string |
| btrfs `open_ctree failed`, no dmesg detail | `block-group-tree`; reformat with `-O ^block-group-tree` |
| `mount(2)` returns ENODEV for a filesystem that exists as a module | `/proc/sys/kernel/modprobe` is `/sbin/modprobeX` — see below |
| No ROG UI in your build | `ROG_UI=n` in `release/src-rt/target.mak` (`.config` is regenerated from it every build) |
| USB stick mounts nowhere and nothing is logged | btrfs/XFS on stock firmware — the fix is the first commit in this branch |
| Clean-tree build dies on `lzo/lzo1x.h` then `libubi.h` in mkfs.ubifs | `mtd-utils-install` passes no include paths; fixed in this branch |
| Image mysteriously MBs too big | `du targets/96813GW/fs/www` — a crashing build helper drops 48 MB `core.<pid>` files there and they get packed in; guard is in this branch |
| Build stops at `syncconfig` with "Error in reading or end of file" | A **new** Kconfig symbol has no answer in `config_base` — every new symbol (and its children: `PSI_DEFAULT_DISABLED`, the four `DEBUG_INFO_*`) needs an explicit line |
| Config edit "didn't take" | `config_gt-be98` = `config_base` + appended block; **last occurrence wins**. Also `KernelConfig` in src-rt/Makefile force-disables PPP_FILTER / XFRM_MIGRATE / NET_KEY_MIGRATE unconditionally |
| 64-bit binary dies `Function not implemented` on another device | The layer glibc is built `--enable-kernel=4.19`: pre-4.19 fallbacks are compiled out. It never runs on older kernels |

**About `modprobeX`:** `rom/etc/init.d/system-config.sh` deliberately sets
`/proc/sys/kernel/modprobe` to `/sbin/modprobeX`, an invalid path. Broadcom's
own comment says it is to stop iptables autoloading kmods with wrong
parameters. The side effect is that the kernel's `request_module()` always
fails, so **any** modular filesystem returns `ENODEV` from `mount(2)`. Don't
"fix" the global knob — that brings the iptables problem back. Load the module
explicitly at the call site, which is what `rc/usb.c` now does.

---

## Backports and the prebuilt-blob rule

The SDK links **114 prebuilt Broadcom kernel objects** (ethernet, wifi,
packet accelerators) compiled against a fixed kernel configuration.  Any
change that moves a field in `task_struct`, `mm_struct`, `struct page`,
or renumbers page-flag / vm-event enums **bricks the boot** — there is no
automatic rollback on BCM6813.  Every backport in this branch obeys one
doctrine, enforced with `pahole`:

> All pre-existing struct member offsets must be byte-identical
> before and after.  New fields go into alignment holes.

Worked examples:

* **PSI (4.20 → 4.19):** upstream adds `psi_flags` (4 bytes) to
  `task_struct`.  Here it lives in the alignment hole after
  `pagefault_disabled` (offset 1908), and the `:1` wake flag packs into a
  half-empty bitfield word (offset 932, 28 spare bits).  pahole confirms:
  size 2688 unchanged, all 150 pre-existing offsets identical.  The
  `mm/filemap.c` hunks were *dropped* — they need `PG_workingset`, and a
  mid-enum page flag renumbers bits the blobs test with baked-in
  constants.  Reclaim/compaction/swap stalls are counted; pagecache
  thrash is not.
* **zswap meminfo (5.19 → 4.19):** the vmstat half was dropped for the
  same reason (`vm_event_item` growth resizes a per-cpu array); the
  meminfo half is pure read-out.
* **zstd 1.5.2 (6.6 → 4.19):** a leaf library — no struct exposure at
  all.  4.19 compat (missing `fallthrough` macro, `size_t` include chain)
  is kept *inside* `lib/zstd/`.
* **zswap LRU / zsmalloc writeback (6.5 → 4.19):** every touched struct
  (`zswap_pool`, `zswap_entry`) is private to `mm/zswap.c`, so this one is
  blob-safe by construction.  4.19 shrinks synchronously from the store
  path, so the LRU reclaim slots into `zswap_shrink()`; the entry header
  becomes unconditional so the swp_entry can be recovered for writeback.

When auditing, build once with `CONFIG_DEBUG_INFO=y` (remember to answer
its four child symbols in `config_base` — see gotchas) and diff
`pahole -C task_struct vmlinux` before/after.

---

## The 64-bit userland layer

The firmware's own userland is 32-bit ARM (glibc 2.32).  `buildFS`
overlays a 64-bit layer from `targets/fs.src/`: glibc 2.43 (built from
source, `--enable-kernel=4.19`), GNU coreutils (single-binary), bash,
htop, zstd, btrfs-progs, xfsprogs, ebtables, nano, iperf3, compsize, and
the supporting libraries.  Current state: glibc **2.44**
(`--enable-kernel=4.19`), gcc **16.2.0** throughout, coreutils 9.11.
The layer's `ldd` carries a dual-arch `RTLDLIST` (aarch64 + the vendor's
32-bit `ld-linux.so.3`) so it can resolve both worlds — that tweak is
baked into the layer build script; hand-edits to fs.src die on the next
clean rebuild, so bake every tweak into the pipeline.
compsize note: Debian's 1.5-1.1 NMU patch (FTBFS #1091561) addresses the
same kerncompat include break we hit; building with
`-DBTRFS_FLAT_INCLUDES=1` plus a two-line shim for `btrfs/{ioctl,ctree}.h`
(pointing at the kernel uapi headers) is functionally equivalent.  **The payload is not in git** — only the buildFS
hook is.  Build your own, or the hook is inert.

Build pipeline for layer binaries (no cross toolchain needed):

```sh
# any aarch64 host, e.g. a container:
docker run --rm -v $PWD:/w ubuntu:24.04 bash -c '
  apt-get update -qq && apt-get install -y gcc make libc6-dev
  # A53 safety: never emit ARMv8.1+ instructions (no LSE!)
  export CFLAGS="-O2 -mcpu=cortex-a53+crypto+crc" ...'
```

Rules learned the hard way:

* The router CPU (Brahma-B53) is **ARMv8.0-A only** — treat it as a
  Cortex-A53.  `-mcpu=cortex-a53+crypto+crc`, always.  Anything built
  with defaults on a modern arm64 host may SIGILL.
* glibc symbol ceiling is **2.43** — build in `ubuntu:26.04` or older.
  (Caveat: some gnulib-based packages fail against 2.43 headers with
  `_Generic` errors — `ubuntu:24.04` builds them fine and the output
  still runs.)
* `PATH` on the router puts `/usr/sbin` before `/usr/bin` — when a
  64-bit tool replaces an in-tree 32-bit one, disable the 32-bit build
  in `target.mak` or it shadows yours.
* ncurses: unversioned references bind fine to a versioned library, the
  reverse does not.  The layer carries Debian-style versioned
  libncursesw/libtinfo with `.so.6` pointing at them.

---

## Related projects

This branch only carries the firmware-side changes. The userland that makes the
new filesystems actually usable is built separately from upstream sources and
dropped onto the router (or into `fs.src`), not vendored here:

| Project | Used for |
|---|---|
| [RMerl/asuswrt-merlin.ng](https://github.com/RMerl/asuswrt-merlin.ng) | The original Asuswrt-Merlin |
| [gnuton/asuswrt-merlin.ng](https://github.com/gnuton/asuswrt-merlin.ng) | The fork this branch is based on — GT-BE98 support lives here |
| [kdave/btrfs-progs](https://github.com/kdave/btrfs-progs) | `mkfs.btrfs`, `btrfs` — cross-built 7.1; see the `-O ^block-group-tree` note above |
| [facebook/zstd](https://github.com/facebook/zstd) | The compressor behind both btrfs `compression=zstd` and zswap |
| [util-linux/util-linux](https://github.com/util-linux/util-linux) | `xfsprogs` companions; `blkid` semantics the `post-mount` script relies on |
| [mirror/busybox](https://github.com/mirror/busybox) | Ships the `volume_id` btrfs/xfs probes this branch switches on |
| [Entware/Entware](https://github.com/Entware/Entware) | The opkg userland on the USB stick (`/tmp/opt`) |
| [htop-dev/htop](https://github.com/htop-dev/htop) | Why `libncursesw.so.6` is already in the image |

`xfsprogs` is maintained on
[kernel.org](https://git.kernel.org/pub/scm/fs/xfs/xfsprogs-dev.git) rather than
GitHub; version 7.1.1 was used for the `mkfs.xfs` flags documented above.

## Licence

Asuswrt-Merlin is GPL; these changes are published under the same terms as the
files they modify.
