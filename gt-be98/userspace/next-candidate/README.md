# Next GT-BE98 userspace candidate

The current candidate combines the verified Web UI NVRAM fix, armel directory
migration, four Ubuntu GCC 15 library builds, and the new
[Ubuntu-style multiarch glibc loaders](../multiarch-loader/README.md).
It is packaged and QEMU verified, **not flashed**. The previous hardware trial
remains recorded in `candidate.json` as `previous_hardware_trial`.

The mandatory preparation pipeline is:

1. Extract the exact runtime-dirs SquashFS pinned in `candidate.json`.
2. Apply the hash-guarded NVRAM getter lifetime fix.
3. Move armel libraries/plugins to `/usr/lib/arm-linux-gnueabi`.
4. Overlay the tested GCC 15 zlib, Expat, json-c and libcap-ng outputs.
5. Apply matched glibc 2.44 runtimes with Ubuntu loader/search-path semantics;
   remove 257 migration aliases and keep 32 documented compatibility entries.

After following both sibling checkpoints' compiler/build instructions:

```sh
python3 scripts/prepare-rootfs.py \
  --base-squashfs /path/to/verified-runtime-dirs-rootfs.squashfs \
  --patch-script ../webui-nvram-cache/scripts/patch-nvram.py \
  --rebuilt ../armel-multiarch/build/libraries/rebuilt \
  --glibc-runtime ../multiarch-loader/packages/runtime \
  --output rootfs --report evidence/integrated-candidate.json
```

Run after legacy installers and overlays. All checkpoint scripts, selected
libraries and the new runtime manifest are pinned. The integrated output
matches the independently staged and unpacked tested SquashFS. All 182 kernel
modules, kernel #36, vendor blobs, prior GNU userspace, merged /usr, /run,
PID1 identity/metadata guard and the Web UI fix are preserved. Systemd is not
installed. USB `/usr/local` and Docker configuration remain the existing
[external runtime dependency](../docker-network-local/README.md).

The 88,333,388-byte PKGTB preserves and verifies the signed #36 bootfs.
Rootfs SHA-256 is `4f2a9673173a0c32b85a2b1256eaafab4ca96312f134df86e38ae1a58595a88e`.
QEMU passes 312 dependency checks without cache and 312 with cache, three ABI
probes, libc and library functional tests, legacy plugin consumers, 34 command
checks, and the PID1 rollback guard with no cache. Actual board operation of
these rebuilt glibc binaries remains to be tested. Do not carry forward the
previous image's physical-test status or firmware commit state as approval of
this new image. Recheck actual UBI capacity and slot state before any flash.
