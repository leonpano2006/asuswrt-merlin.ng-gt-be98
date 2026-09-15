# Next GT-BE98 userspace candidate

The next firmware candidate must include the verified NVRAM cache getter fix
from `699d70ef091de2de2d9d5409601084d1410a6fa6` directly in its rootfs. This is
a candidate checkpoint; no new firmware image or hardware flash is requested.

`candidate.json` pins the previously flashed runtime-dirs SquashFS and the
patch generator/input/output hashes. `prepare-rootfs.py` extracts that exact
baseline into a new offline directory and applies the fix. Its full inventory
comparison requires exactly one changed path, `usr/lib/libnvram.so`, with
unchanged mode and no added/removed files. Kernel modules and previous
userspace/layout changes are therefore preserved. The generator and tests
remain in the adjacent `webui-nvram-cache` directory, avoiding duplicate code.

From this directory in the firmware repository:

```sh
python3 scripts/prepare-rootfs.py \
  --base-squashfs /path/to/verified-runtime-dirs-rootfs.squashfs \
  --patch-script ../webui-nvram-cache/scripts/patch-nvram.py \
  --output rootfs --report evidence/staged-rootfs.json
```

Use this prepared rootfs for the next SquashFS, after all legacy installers
and userspace overlays. Preserve zstd level 22, 512 KiB blocks and root
ownership. Recalculate compressed size/UBI capacity and perform the usual
packaging, signature-preservation and boot validation when producing the next
image. The previous packer's exact rootfs hash describes the old image and
must be reviewed for the newly produced artifact; do not remove its checks.

The patched library is already validated by offline regressions, native
isolated tests and the live management-service overlay. The user confirmed
normal operation. The next complete firmware is not yet packaged or boot
tested. The separately rebuilt B53 glibc package is not added by this item;
the baseline's tested glibc 2.44 remains in place.

Once this rootfs is used, the library is available without a USB fix mount.
The current USB helper also detects the already-patched hash and does not
overlay/restart it. This checkpoint leaves the running router and its
uncommitted slot-1 / committed slot-2 rollback state unchanged.

## USB runtime dependency: Docker networking

The running router now also uses the verified
[Docker networking and USB /usr/local checkpoint](../docker-network-local/README.md).
Its binaries, bridge/NAT configuration and Merlin hook integration reside on
the USB, outside this SquashFS. Keep that runtime checkpoint with this candidate
when restoring or deploying the device. See its install manifest and validation
record for exact dependencies and tested limits. The staged firmware rootfs and
its Web UI patch are unchanged by this USB integration.
