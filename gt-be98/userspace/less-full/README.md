# GT-BE98 full less 704

Replace the BusyBox `less` applet with the full, unpatched upstream release at
`/usr/bin/less`. Include `lesskey`, `lessecho`, `less-osc8-open` and the three
manual pages in the firmware candidate. The runtime dependencies are the existing
firmware glibc 2.44 and `libtinfo.so.6`; Entware is not required.

The native DGX build uses GCC 16.2.0, `-mcpu=cortex-a53+crc+crypto`, `-Oz`, LTO,
stack protection, RELRO/NOW and a GNU SHA-1 build ID. The upstream tarball is
pinned by SHA-256 and its official package signature is verified. A build ID is
an identifier, not a cryptographic signature of our binary. The default full
feature set is enabled, with glibc POSIX regular expressions, terminfo, UTF-8,
runtime secure mode and the editor/shell features supported by upstream.

## Live installation

The running a3 firmware is read-only SquashFS. Its old less symlink points to
BusyBox, so bind mounting onto that symlink would cover BusyBox itself. Instead,
`live/apply-live.sh` builds a read-only OverlayFS with two lower directories:
four package files copied into RAM, plus a private bind of the original
`/usr/bin`. It first tests this view at a private mountpoint and then installs
the view at `/usr/bin`. Other entries and the BusyBox binary remain intact.

The payload and manuals are stored at `/jffs/leon-less-704` on the USB-backed
JFFS mount. A small addition to the existing `local-mount` hook restores it
after USB initialization. This hook applies only to a3/#36, leaves the
committed fallback alone, and skips firmware that already contains native
full less. No flash, reboot or firmware commit is part of this installation.
The hook was executed twice successfully; a reboot was not performed.

Entware prepends `/opt/bin` in login shells. `live/pager-profile.sh`, sourced
from the existing JFFS profile before the bash handoff, therefore selects
`PAGER=/usr/bin/less`, `SYSTEMD_PAGER=/usr/bin/less` and systemd secure mode
explicitly. This retains the user's other PATH preferences. A bare shell
`less` command can still resolve to Entware; `/usr/bin/less` and systemd use
the new firmware build.

For manual reversal on this running firmware: first restore
`/jffs/leon-less-704/local-mount.before` to `/jffs/scripts/local-mount`, then
unmount `/usr/bin` and `/run/leon-less-704/original`. Do not remove RAM backing
files while the overlay is mounted. The original SquashFS content is unchanged.
Restore `profile.add.before` from the same payload directory to
`/jffs/configs/profile.add` to undo the login pager selection as well.

Live tests use real SSH PTYs and verify `/proc/.../exe` points to `/usr/bin/less`.
They cover default `systemctl` and `journalctl` paging, scroll/quit, UTF-8,
ANSI color and regular-expression search. Systemd supplies `LESS=FRSXMK` and
`LESSSECURE=1`. Raw journal/terminal logs remain in the private backup, not Git.

## Firmware candidate and replay

This is an out-of-tree addition to `systemd-upgrade-20260917`, whose published
parent is `66b518eb544205d05ed57f99c89ebde07bf1a704` on
`gt-be98-systemd257-services`. Restore that checkpoint and its documented
dependencies before rebuilding. It is not a standalone SDK. The GCC compiler
remains in its separate toolchain project.

```sh
python3 less-full-20260917/scripts/fetch-source.py
python3 less-full-20260917/scripts/prepare-sdk.py
python3 less-full-20260917/scripts/build.py
python3 less-full-20260917/scripts/prepare-root.py
python3 less-full-20260917/scripts/pack-rehearsal.py --revision less704-systemd257
python3 less-full-20260917/scripts/run-qemu.py --label less704-systemd257 --kernel multiarch-loader-20260916/saved-inputs/Image36 --initrd less-full-20260917/build/less704-systemd257/guest.cpio.gz --timeout 180
python3 less-full-20260917/scripts/run-qemu.py --label less704-services257 --kernel multiarch-loader-20260916/saved-inputs/Image36 --initrd less-full-20260917/build/less704-systemd257/guest.cpio.gz --timeout 180 --target services
python3 less-full-20260917/scripts/pack.py
```

The SDK uses recorded ncurses 6.4 declaration headers with the existing ncurses
6.6 ABI-6 tinfo runtime. Their hashes are saved; no host libraries are linked.
The full SDK, upstream source, build outputs and candidate are privately backed
up. Compilation logs record all options, including the CPU target; LTO objects
retain `.GCC.command.line` when the linked ELF does not.

The candidate directly installs regular files into SquashFS and does not need
the live overlay. `prepare-root.py` explicitly unlinks the BusyBox alias before
copying less and verifies every other existing file is unchanged. Full systemd
and service QEMU regressions run again with the actual less-equipped rootfs.
Hardware backends remain the same documented test substitutes as in the parent.

Compression stays at zstd 22, 1 MiB blocks and tail packing. Grouping by ELF
family and basename fits the existing 734-LEB capacity without deleting content
or reducing the vendor's 1 MiB reserve per volume. Capacity must be read again
before a future flash. The signed bootfs, kernel, all modules, early init and
rollback state are unchanged. The systemd 257 firmware is still an unflashed
candidate; only this less package has passed live testing on systemd 255.

Final image: `GT-BE98_leon36-systemd257-less704_zstd22.pkgtb`, 90,971,212 bytes,
SHA-256 `2fc6927dddce088b2ed631bf0cf70c026a73a1e554b0c5b93e20eba3736dc38f`.
The rootfs is 78,553,088 bytes, requiring 107 + 627 reserved LEBs in total.
Full QEMU regression passed in 106.38 seconds; service regression in 33.85
seconds. Both reached orderly poweroff with no kernel panic.

Official source: https://greenwoodsoftware.com/less/download.html
