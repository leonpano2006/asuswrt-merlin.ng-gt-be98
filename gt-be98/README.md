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

Six commits, each self-contained. The first four are not GT-BE98-specific and
should apply to any HND 5.04 BE / 4916 target.

| Commit | What | Notes |
|---|---|---|
| `usb: detect and mount btrfs and xfs USB partitions` | Makes btrfs/XFS sticks automount | Verified on hardware |
| `build: expose the kernel's own menuconfig` | `make kernel-config-prep` / `kernel-menuconfig` | Tooling only |
| `nfs: build nfs-utils and portmap against libtirpc` | Fixes NFS under glibc 2.32 | Compiles; portmap change **not runtime-tested** |
| `buildFS: install the aarch64 glibc layer and GNU coreutils` | 64-bit userland layer | Inert without the `fs.src` payload |
| `kernel: GT-BE98 config` | btrfs, XFS, zram/zswap, WireGuard, overlayfs, namespaces | Opinionated |
| `GT-BE98: local build settings` | ROG UI on, NFS off, build tag | **Drop this one when rebasing** |

To rebase onto a newer upstream tag:

```sh
git fetch upstream --tags
git rebase --onto <new-tag> <old-tag> gt-be98
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

**About `modprobeX`:** `rom/etc/init.d/system-config.sh` deliberately sets
`/proc/sys/kernel/modprobe` to `/sbin/modprobeX`, an invalid path. Broadcom's
own comment says it is to stop iptables autoloading kmods with wrong
parameters. The side effect is that the kernel's `request_module()` always
fails, so **any** modular filesystem returns `ENODEV` from `mount(2)`. Don't
"fix" the global knob — that brings the iptables problem back. Load the module
explicitly at the call site, which is what `rc/usb.c` now does.

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
