# ASUS BusyBox AArch64 candidate — 2026-09-23

The existing ASUS BusyBox 1.25.1 builds and runs as ELF64/AArch64 on BE98.
This is an independently tested candidate, not a BusyBox version upgrade or a
replacement of the system binary. No daemon was restarted, firmware flashed,
router rebooted or boot metadata changed.

## Build and dependencies

The DGX used GCC 16.2.0, glibc 2.44 and `-mcpu=cortex-a53+crc+crypto`.
The ARMEL baseline uses GCC 15.2.0; size differences include compiler and ABI
changes and cannot be attributed solely to AArch64. The config is identical
except its generated timestamp, and all 157 applets match. ASUS source changes,
HND/BE4916/security/logging defines and the previous time64 fix are retained.
ARM32 instruction flags and the forced __ARM_ARCH_7A__ macro are removed.

The old build supplied ARM32 libptcsrv, but its executable did not depend on it.
Its callers depend on FEATURE_TELNETD_CLIENT_TO_ENV, already disabled in both
builds. The new build omits that unused library and vendor search directory.
No existing feature was disabled to make this build succeed. Internal BusyBox
crypt remains enabled.

On BE98 the candidate resolves libc, libm, libgcc_s, its loader and the existing
`/usr/$LIB/libleon-rc-notify.so` preload entirely to AArch64 libraries.
This does not make the whole firmware 64-bit: existing ARM32 ASUS processes
still need ARMEL libraries. Both 32-bit-to-64-bit and reverse process exec
were tested; there is no mixing of library architectures inside one process.

## Size

| Measure | ARMEL | AArch64 | Reduction |
| --- | ---: | ---: | ---: |
| Stripped file bytes | 657148 | 592528 | 64620 (9.83%) |
| Single-file zstd --ultra -22 -T1 bytes | 309843 | 287648 | 22195 (7.16%) |
| ELF text + data bytes | 610016 | 571982 | 38034 |

BSS grows from 1480 to 1760 bytes. Compressed file figures are not SquashFS
image savings; full-image packaging and capacity checks remain necessary.
SHA-256: `2931fe7011b56e4de43bb53ae87377037bfe3779295c5baa2ca3fe4b04915f28`.
ELF Build ID: `a503b6657ee2dbe6f7596eaef3cd82202fcd85bf` (not a signature).

## Verification and remaining work

DGX checks passed for shell arithmetic, text tools, copy/tar, a 5 GiB sparse
file size, post-time32 date (2038-01-19T03:14:08Z), process/mount/filesystem
queries, and the matching applet list. The target glibc was explicitly loaded;
libgcc resolved to the host's existing AArch64 libgcc. The first exploratory
script tried stat, absent in both builds, and stopped; the saved corrected
script uses the enabled ls applet and passed.

Independent BE98 checks passed for the applet list, shell/text/file/archive
operations, post-2038 date, cross-architecture exec, process/mount/filesystem
queries, DNS and ping. Loopback, gateway, Cloudflare and Sydney via DNS each
received 3/3 replies (12/12 total), with mean RTT 0.155, 0.417, 1.224 and
291.353 ms. A TTL=1 test with a three-second deadline exited status 1 after
three seconds. HTTPS management returned 200, systemd had zero failed units,
and the installed BusyBox hash remained unchanged.

Both old and new logread return status 1: the active system has no syslogd
shared-memory buffer. Source headers use fixed-width int32_t fields, but no
successful runtime IPC test is claimed. Logging/DHCP daemon, login
authentication, USB hotplug and mount-action regression tests remain before
replacing system BusyBox. IPv6 and complete reboot behavior were not tested.

Router test file: `/tmp/leon-busybox-aarch64-20260923/busybox-aarch64`.
It is not installed over /usr/bin/busybox and is not persistent.

## Reproduction scope

build.py, check-host.py and check-router.bash preserve the executed recipe and
checks. They require the existing DGX workspace layout, prior checkpoint's
config/patched time.c, compiler/sysroot and local archives. They are not a
standalone clean SDK recipe. The build refuses to overwrite existing sources.

Archive input SHA-256:
- bb-src.tgz: `11b0df76187090750fb4d3944c3f8028e88adcc3f0cd4b5ee70c9ac0de3a3837`
- bb-kit.tar: `3d8108fabf1f4ad8a45e01e6218c584123848c8ac66577e3084c57a42825dc32`

These archives have historical vendor/helper/generated-header differences from
the full SDK. The clock fix is already on main in f80c68e. Publication includes
actual architecture build/test scripts and results, not the binary, toolchain,
private logs or unrelated historical source differences. The toolchain remains
an external dependency/repository.
