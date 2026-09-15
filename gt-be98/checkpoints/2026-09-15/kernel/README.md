# Kernel configurations and native build

`configs/acl35.config` is the confirmed #35 configuration. It enables
core cgroups, pids, devices, freezer, cpuacct, seccomp, veth/macvlan and
Btrfs POSIX ACL. `configs/memcg36.config` adds `GTBE98_MEMCG_ABI`, MEMCG,
MEMCG_SWAP, MEMCG_SWAP_ENABLED and PAGE_COUNTER. MEMCG_KMEM remains off.

These options preserve the measured Leon #32 binary layout, not arbitrary
ARM64 configurations:

| Structure | Size (bytes) | Placement |
|---|---:|---|
| task_struct | 2688 | cgroups/cg_list at 144/152, seccomp at 168, memcg fields in tail padding |
| page | 64 | mem_cgroup at 56 in existing padding |
| mm_struct | 848 | owner allocated after dynamic cpu_bitmap; init_mm has separate storage |
| lruvec | 128 | single-node pgdat accessor, no extra member |
| pglist_data | 5312 | original layout retained |
| kmem_cache | 240 | unused slab-accounting members excluded |

Kconfig restricts this to ARM64 BCM96813, SMP, SLUB and a single memory
node. Compile-time assertions protect the measured offsets and sizes.
Do not enable other layout-changing controllers without repeating the
ABI comparison, QEMU module matrix and hardware tests.

## Rebuild an isolated SDK tree

Use an AArch64 build host and the GCC 10.3 Buildroot kernel SDK from
[am-toolchains-aarch64 v2021.02.4-1](https://github.com/leonpano2006/am-toolchains-aarch64/releases/tag/v2021.02.4-1).
The pinned assets, compiler triplets and SHA-256 values are in
[dependencies.json](dependencies.json). This repository consumes the SDK;
Buildroot source and SDK binaries remain in that separate repository.
Use its AArch64-target SDK
(`aarch64-buildroot-linux-gnu-`). GCC 16.2 in the USB recipe is a separate
userspace compiler. The SDK source and proprietary prebuilts must already
be present. Run the SDK relocation script after extraction. The native
wrapper generates Broadcom Kconfig/Makefile metadata and its version header,
stages the tracked GT-BE98 HND directories, and prepares the WLAN and RDP
links normally supplied by the top-level firmware build. If the platform
or router feature config is absent, it copies the saved `platform.config`
and `router.config`; it leaves existing configs and HND directories intact.
Use a disposable checkout to avoid carrying unrelated generated state into
the build. Do not build on the router.

From the repository root, for #36:

```sh
cp gt-be98/checkpoints/2026-09-15/kernel/configs/memcg36.config \
  release/src-rt-5.04behnd.4916/kernel/linux-4.19/.config
export GTBE98_SDK=/path/to/br-aarch64/output/host
python3 gt-be98/checkpoints/2026-09-15/kernel/build-kernel.py \
  --label memcg36 --version 36 --target olddefconfig
python3 gt-be98/checkpoints/2026-09-15/kernel/build-kernel.py \
  --label memcg36 --version 36
python3 gt-be98/checkpoints/2026-09-15/kernel/build-kernel.py \
  --label memcg36-lib --version 36 --target modules --module-dir lib
python3 gt-be98/checkpoints/2026-09-15/kernel/build-kernel.py \
  --label memcg36-crypto --version 36 --target modules --module-dir crypto
python3 gt-be98/checkpoints/2026-09-15/kernel/build-kernel.py \
  --label memcg36 --version 36 --target modules --module-dir fs/btrfs
```

The build host needs Python 3, GNU make, GCC/G++, flex, bison, bc, Perl
and the normal Linux kernel host development dependencies.

The script routes through `build/Bcmkernel.mk` to preserve Broadcom's
environment and `KCFLAGS=-DGTBE98`. For #35 use its saved config and build
number. Compare the normalized config against the input before packaging.
Btrfs's module build needs `lib/Module.symvers` and `crypto/Module.symvers`;
the two preceding module commands generate these and the raid6/xor modules.
The command records
logs and config hashes below this checkpoint's ignored `builds/` directory.

The full `modules` target is **not** known to complete: the provided tree
lacks `drivers/char/mxl/mxl.o`. The tested images use a rebuilt Btrfs module
and preserve the other existing module payloads. Do not fabricate missing
objects or treat a kernel-only build as a complete firmware build.

For a future SDK profile integration, preserve the full saved config and
pass the enabled controller symbols through `EXTRA_KERNEL_YES_CONFIGS`;
the SDK may otherwise overwrite a manually edited `.config`. Keep the
trial init/boot safeguards in the matching rootfs.
