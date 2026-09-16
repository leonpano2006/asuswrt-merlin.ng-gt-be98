# Next GT-BE98 userspace candidate

The current candidate adds [GCC runtimes](../libgcc-runtime/README.md) to the
previously hardware-tested Ubuntu-style multiarch firmware. Armel moves from
GCC 10.3 to Ubuntu GCC 15.2, armhf gains GCC 15.2, and the existing aarch64 GCC
16.2 library is retained. QEMU and isolated runtime probes on the router pass;
the newly packaged complete image has not yet been flashed. The current prior
image is under `previous_hardware_trial` in candidate.json; older trials remain
under `earlier_hardware_trials`.

The mandatory preparation pipeline is:

1. Extract the pinned runtime-dirs SquashFS.
2. Apply the hash-guarded NVRAM getter lifetime fix.
3. Move armel libraries/plugins to `/usr/lib/arm-linux-gnueabi`.
4. Overlay tested GCC 15 zlib, Expat, json-c and libcap-ng builds.
5. Apply glibc 2.44 with Ubuntu loader/search-path semantics; remove 257
   migration aliases and keep 32 documented compatibility entries.
6. Apply the pinned libgcc overlay: replace armel and add armhf only.

After following the three sibling checkpoints' dependency/build instructions:

```sh
python3 scripts/prepare-rootfs.py \
  --base-squashfs /path/to/verified-runtime-dirs-rootfs.squashfs \
  --patch-script ../webui-nvram-cache/scripts/patch-nvram.py \
  --rebuilt /path/to/verified-four-library-outputs \
  --glibc-runtime ../multiarch-loader/packages/runtime \
  --libgcc-runtime ../libgcc-runtime/packages/runtime \
  --output rootfs --report evidence/integrated-candidate.json
```

Run after legacy installers and overlays. Scripts, selected libraries and
runtime manifests are pinned. The full pipeline output matches both the
independent staging tree and unpacked tested SquashFS. All 182 kernel modules,
kernel #36, vendor components, previous GNU userspace, merged /usr, /run,
PID1 identity/metadata guard and the Web UI fix are preserved. Systemd is not
installed. USB `/usr/local` and Docker remain the existing
[external runtime dependency](../docker-network-local/README.md).

The 88,370,252-byte PKGTB preserves and verifies the signed #36 bootfs.
Its SHA-256 is `e1007e8210f357e1a6f7a3c8c899706644f953a84f05f5283859a948935460e0`.
Rootfs SHA-256 is `274ad17ea4c9878352a9648acfe8c4ce2057043b30068e0e410102df21fce3d6`.
QEMU passes 624 dependency checks, three ABI probes, prior library/userspace
checks, the PID1 guard and four new unwind/C++ cases including old GCC 10
consumers. Those four runtime cases also pass in isolated temporary processes
on the physical router. See
[the runtime verification](../libgcc-runtime/evidence/verification.json).

The [previous complete firmware trial](../multiarch-loader/flash/evidence/live-summary.json)
also passed Web UI, four radios, Docker networking/memcg and Runner checks.
Those observations refer to the previous image, not a boot of this new image.
Slot 1 remains uncommitted; normal reboot goes to committed slot 2 / #35.
Recheck live UBI capacity and slot state before any future flash.
