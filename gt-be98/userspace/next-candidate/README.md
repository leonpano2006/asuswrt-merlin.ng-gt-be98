# Next GT-BE98 userspace candidate

The current candidate adds [Cortex-A53 runtimes](../a53-runtimes/README.md):
libgcc and libstdc++ for armel/armhf with GCC 15.2, aarch64 with GCC 16.2,
and the four existing armel C libraries. All are rebuilt on DGX against
matching glibc 2.44 sysroots with CRC/Crypto enabled and retained SHA-1 Build IDs.
QEMU, isolated runtime tests and the complete firmware trial on the router pass.
See the [current physical trial](../a53-runtimes/flash/README.md). Prior hardware
trials remain separately recorded in `candidate.json`.

The mandatory preparation pipeline is:

1. Extract the pinned runtime-dirs SquashFS.
2. Apply the hash-guarded NVRAM getter lifetime fix.
3. Move armel libraries/plugins to `/usr/lib/arm-linux-gnueabi`.
4. Overlay the preceding tested GCC 15 zlib, Expat, json-c and libcap-ng builds.
5. Apply glibc 2.44 with Ubuntu loader/search-path semantics; remove 257
   migration aliases and keep 32 documented compatibility entries.
6. Apply the preceding generic libgcc overlay as its pinned checkpoint input.
7. Replace the runtimes with the ten A53 builds and their multiarch SONAME links.

After restoring the sibling checkpoints' pinned dependency/build inputs:

```sh
python3 scripts/prepare-rootfs.py \
  --base-squashfs /path/to/verified-runtime-dirs-rootfs.squashfs \
  --patch-script ../webui-nvram-cache/scripts/patch-nvram.py \
  --rebuilt /path/to/verified-four-library-outputs \
  --glibc-runtime ../multiarch-loader/packages/runtime \
  --libgcc-runtime ../libgcc-runtime/packages/runtime \
  --a53-runtime ../a53-runtimes/packages/runtime \
  --output rootfs --report evidence/integrated-candidate.json
```

Run after legacy installers and overlays. Scripts, selected libraries and
runtime manifests are pinned. The complete pipeline output matches independent
staging and unpacked SquashFS. All 182 module files, kernel #36, vendor blobs,
previous GNU userspace, glibc 2.44, merged /usr, /run, PID1 identity/metadata guard
and the Web UI fix are preserved. No new flat library aliases or systemd are
installed. USB `/usr/local` and Docker remain the existing
[external runtime dependency](../docker-network-local/README.md).

The 89,439,308-byte PKGTB preserves and verifies the signed #36 bootfs.
SHA-256: `7d48c2274be8dae6179096208a738d5214b321805b6d1fa9f0736bf23eff92f9`.
Rootfs SHA-256: `68888e499d0095374266c8f2adf0be296c5370e893c81c548e7a36c1030e9216`.
QEMU passes 624 executable dependency checks, three glibc ABI probes, prior
library/userspace checks, the PID1 guard, five unwind/cross-DSO C++ cases and
ten C++ dual-ABI tests. The same runtime tests pass on the physical router.
739 public versioned dependency checks also pass. The 11 removed GCC 10
internal weak inline exports are explicitly documented and unreferenced by
firmware; external consumers of those names require separate validation.
See [runtime verification](../a53-runtimes/evidence/verification.json).

The [current complete firmware trial](../a53-runtimes/flash/evidence/live-summary.json)
passes installed-runtime, Web UI, four-radio, Docker networking/memcg and Runner
checks. All 244 installed library hashes match, and normalized network state,
88 loaded module names and 18 hook/config fingerprints match baseline.
Slot 1 remains uncommitted; normal reboot goes to committed slot 2 / #35.
Current UBI arithmetic leaves 12 eraseblocks after reserving the new payloads;
recheck capacity and boot state immediately before any future flash.

The installed [multiarch ldd entry fix](../ldd-multiarch/README.md) is an external
runtime dependency: `/usr/local/bin/ldd` and `/opt/bin/ldd` point to the existing
firmware `/usr/bin/ldd`. All three ABIs and Entware programs pass its tests.
