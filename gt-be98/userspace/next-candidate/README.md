# Next GT-BE98 userspace candidate

The next candidate combines the verified Web UI NVRAM cache fix with
[armel multiarch and Ubuntu GCC 15 library rebuilds](../armel-multiarch/README.md).
The final SquashFS passed QEMU checks using the exact #36 kernel, then was
packaged and tested on the physical GT-BE98. It is running as an uncommitted
slot-1 trial with the committed #35 fallback retained in slot 2. See the
[hardware trial record](../armel-multiarch/flash/README.md).

The preparation pipeline is mandatory and ordered:

1. Extract the exact runtime-dirs SquashFS pinned in `candidate.json`.
2. Apply the NVRAM getter lifetime fix from
   `699d70ef091de2de2d9d5409601084d1410a6fa6`. The base-stage inventory comparison
   requires exactly one changed file: `usr/lib/libnvram.so`.
3. Move armel libraries and private plugins into `/usr/lib/arm-linux-gnueabi`,
   preserving old ABI paths as links and adding ld.so.conf.d fragments.
4. Overlay the tested Ubuntu GCC 15 builds of zlib, Expat, json-c and libcap-ng.
   Check input/output hashes, ELF ABI, SONAME and exported symbol compatibility.

`prepare-base-rootfs.py` preserves the independently checked first two stages.
`prepare-rootfs.py` is the complete candidate entry point. It requires all four
libraries; it does not silently omit the new multiarch/compiler changes.
The rootfs output must be a new offline directory.

From this directory in the firmware repository, after following the adjacent
armel checkpoint's compiler and library build instructions:

```sh
python3 scripts/prepare-rootfs.py \
  --base-squashfs /path/to/verified-runtime-dirs-rootfs.squashfs \
  --patch-script ../webui-nvram-cache/scripts/patch-nvram.py \
  --rebuilt ../armel-multiarch/build/libraries/rebuilt \
  --output rootfs --report evidence/integrated-candidate.json
```

Run this after all legacy installers and userspace overlays. The staged
candidate and the integrated recipe produce identical file/link inventories.
All 182 kernel modules, glibc 2.44, previous Leon userspace, merged /usr,
/run layout, and the PID1 boot-metadata guard are preserved. Systemd is not
installed by this checkpoint.

Package SquashFS with zstd level 22, 512 KiB blocks and root ownership. The
validated SquashFS is 75,804,672 bytes, SHA-256
`9d13b0b5789843e691cf08f2083c189dbc61f48eeb5d433795183e455b4aa026`.
The 16 KiB increase over the base is not a substitute for checking the final
PKGTB/UBI size. The tested PKGTB is 88,222,796 bytes with 21 UBI eraseblocks
remaining. It preserves the signed #36 bootfs bytewise; signature and complete
image readback checks passed. Future packaging must repeat these checks.
Do not remove the packer's exact-input checks or change firmware commit metadata.

QEMU passed all 312 dynamic-program dependency checks, 34 userspace command
checks, armel/armhf/aarch64 ABI probes, the four rebuilt-library functional
checks, module paths and the existing init/rollback guard probes. QEMU does
not establish full physical-board service or accelerator behavior.

The NVRAM patch is now part of the rootfs at its canonical armel location,
reachable through the old `/usr/lib/libnvram.so` link. Its existing USB helper
recognizes the patched bytes and avoids a redundant overlay/restart. The
hardware trial confirmed httpd maps the canonical armel library without a
USB bind overlay. Authenticated Dashboard and System Information pages update
normally. Physical tests also passed all 312 executable dependency checks,
the three ABI probes and the four rebuilt-library functional checks.

The four radios and Runner acceleration are active. Docker DNS, HTTP, HTTPS,
service-name resolution and a published LAN port passed after reboot. The
boot log completed without a detected kernel/userspace fault. The firmware
has not been committed: slot 1 is commit=0 and slot 2 is commit=1; normal
reboot currently returns to #35.

## USB runtime dependency: Docker networking

Keep the verified [Docker networking and USB /usr/local checkpoint](../docker-network-local/README.md)
with this candidate when restoring or deploying the device. Its Docker
binaries, bridge/NAT configuration and Merlin hook integration reside on USB,
outside the SquashFS. Existing container data and user customizations remain
part of that runtime checkpoint.
