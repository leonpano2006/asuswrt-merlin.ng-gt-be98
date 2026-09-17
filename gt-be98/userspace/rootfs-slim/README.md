# GT-BE98 further rootfs slimming measurements

2026-09-17. DGX-only experiments. No router writes, flash, firmware commit,
UBI changes, or changes to the existing leon5 firmware candidate.

## Result

Further reduction is possible, but the measured optimizations alone do not
fit the full OpenSSL 4 addition into the current slot1 allowance.

| Configuration | Rootfs bytes | Saving versus original full OpenSSL 4 probe | Headroom versus slot1 limit |
| --- | ---: | ---: | ---: |
| Original OpenSSL 4 -O2 / packer zstd 1.5.5 | 81,633,280 | 0 | -3,067,904 |
| Identical files / packer zstd 1.5.7 | 81,272,832 | 360,448 | -2,707,456 |
| OpenSSL 4 -Oz + LTO / packer zstd 1.5.7 | 80,953,344 | 679,936 | -2,387,968 |
| Above plus four applications on USB, capacity simulation only | 77,697,024 | 3,936,256 | +868,352 |

All use SquashFS zstd level 22, 1 MiB blocks, tailends, and family-name ordering.
The 78,565,376-byte limit preserves the previously observed slot1 allocation
and vendor's extra 1 MiB per-volume reserve. It must be rechecked before flashing.
The last row is NOT a deployable image: it substitutes USB symlinks for Tor,
Ookla, iperf3, and the sqlite3 command-line executable. All shared libraries
remain in the image. The four originals are saved under build/usb-payload.
Boot/service ordering, stale configuration, unmounted-USB behavior, and service
dependency audits remain to be implemented before any real migration.

These measurements still use the original leon5 systemd binaries. Enabling its
OpenSSL/ZSTD/ZLIB/CURL features and adding other pending updates can cost more
space. Even 868,352 bytes of simulated headroom is not a guarantee for that work.

## What changed and was verified

- The host mksquashfs 4.6.1 had been using libzstd 1.5.5 even though firmware
  contains 1.5.7. An isolated loader invocation selects existing target glibc
  2.44 plus libzstd 1.5.7 for the packer; no host library is replaced.
- That 352 KiB saving changes no file content, mode, or symlink. Unpack comparison
  passes for 4,692 paths, and the exact #36 kernel reads and hashes all 3,556
  regular files successfully in a bounded offline QEMU guest.
- Unmodified OpenSSL 4.0.2 is rebuilt with GCC 16.2, glibc 2.44,
  `-mcpu=cortex-a53+crc+crypto`, `-Oz -flto=8`, stack protection, RELRO/NOW,
  and SHA1 GNU build IDs. Build IDs are identifiers, not digital signatures.
- The OpenSSL configured feature set and exported API names/versions match
  the previous full build. No algorithms, providers, or CLI are disabled.
  Only its four newly added ELF files differ; all pre-existing firmware files
  are unchanged, including hardware modules, ASUS ARM32 TLS and CLI, and init.
- Seven selected upstream groups / 334 tests pass using target glibc. The #36
  Cortex-A53 guest passes cross-ABI signatures and bidirectional TLS 1.3 with
  ARM32 OpenSSL 3.5.8, systemd 257 encrypted-credential round trip, and legacy
  provider loading. Hardware performance and full firmware boot are untested.
- Five alternative sort strategies with the original packer all increased size
  by 98,304–417,792 bytes. Existing duplicate elimination, 1 MiB blocks, and
  previous ADSL removal are already counted; their savings cannot be counted again.

The optimized image SHA256 is
`82b8b17c28458c84852673893feba5255a253d59883288171f9e720abe2c3e9c`.
The hypothetical optimized USB-split image SHA256 is
`3038dabac9456a0bc0bff1dd262baeae7f94c9c28ebc7e2ce5867d771b0881b6`.

An initial optimized measurement used build-tree 0775 file modes. Final staging
restores the original overlay's file modes. Bytes tested in QEMU are identical;
the final SquashFS hash changes but its size does not. Keep the `-final` result
as authoritative. No final firmware package was generated.

## Replay and dependencies

Requires the previous userspace-refresh checkpoint at candidate-branch commit
830c09df1194ae26ce8b07e790fe2df5837dbbe2, its pinned OpenSSL tar/source, SDK and
compiler wrapper; the separate GCC 16.2 and A53-runtime trees; leon5 production
root; systemd-rc-next's sorting script; multiarch-loader's inventory helper and
exact Image36; and the saved a53-runtime/crypto-v2 initramfs fixtures.
This is deliberately out-of-tree work, not a replacement firmware source tree.

In a clean checkpoint output directory:

1. Run scripts/build-small-openssl.py (bounded -j8 build, LTO may take minutes).
2. Run scripts/measure.py on the previous size-probe-rootfs with label
   packer-zstd157 and --zstd157; then scripts/verify-packing.py.
3. Run scripts/measure-usb-split.py (capacity simulation only).
4. Run scripts/stage-optimized.py and scripts/test-optimized.py.

Scripts refuse existing output roots/images. Evidence records actual commands,
hashes, sizes and tests. Do not treat the USB simulation or either oversized
all-in-flash measurement as a flashable candidate.
