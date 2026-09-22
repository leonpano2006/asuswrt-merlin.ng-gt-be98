# BE98 BusyBox time64 clock fix — 2026-09-22

The ARM32 BusyBox on the leon10 runtime received ICMP replies but reported
incorrect round-trip times, including approximately 4,294,827 ms on loopback.
Its direct legacy `clock_gettime` syscall wrote an 8-byte kernel time32
structure into glibc 2.44's 16-byte userspace time64 `struct timespec`.

`release/src/router/busybox/libbb/time.c` now calls libc `clock_gettime()` when
`__USE_TIME_BITS64` is active. Other builds keep the existing syscall path.
On the running 4.19.294 kernel, glibc correctly falls back from the unavailable
time64 syscall and translates the legacy result. No kernel change is needed.

## Verification

`clock-abi-probe.c` reproduced the structure mismatch: `time_t=8`,
`timespec=16`, nanosecond offset 8, and the last eight bytes remained at the
probe's sentinel value after the raw syscall. The libc path and a 50 ms sleep
measurement returned sensible values.

The rebuilt BusyBox was tested on the router against loopback, the LAN
gateway, Cloudflare and Google anycast, and public test endpoints in
[Amsterdam](https://ams.lg.speedypage.com/),
[Ashburn](https://ash.lg.speedypage.com/),
[Tokyo](https://tyo.lg.speedypage.com/), and
[Sydney](https://syd.lg.speedypage.com/), including Sydney via DNS.
All 45 probes received replies. Mean RTTs ranged from 0.144 ms on loopback
to 291.469 ms to Sydney. Details are in `result.json`.

The normal system ping entry was tested after deployment. A TTL=1 test with
a three-second deadline exited with status 1 after three seconds, without
hitting an outer six-second timeout. The 157-applet list and shared-library
dependencies were unchanged. Basic shell, file, date, uptime and ps checks
passed; the management interface returned HTTP 200 and systemd had no failed
units. IPv6 is disabled on this router and was not enabled or validated.
These are short functional checks, not exhaustive applet or network testing.

## Build and integration status

The live binary was rebuilt on the DGX with the existing ARMEL GCC 15.2.0
toolchain and glibc 2.44 sysroot. Flags include
`-mcpu=cortex-a53+crypto -march=armv8-a+crc+crypto
-mfpu=crypto-neon-fp-armv8 -mfloat-abi=softfp`, preserving the soft-float ABI.

The archived BusyBox build input has historical vendor/helper/generated-header
differences from the complete SDK. Its original `libbb/time.c` was verified
byte-for-byte identical to main before applying this patch. Those unrelated
archive differences are not introduced by this commit. This checkpoint does
not claim a clean, standalone SDK build or publish the live binary.

Local build input SHA-256 values:

- `bb-src.tgz`: `11b0df76187090750fb4d3944c3f8028e88adcc3f0cd4b5ee70c9ac0de3a3837`
- `bb-kit.tar`: `3d8108fabf1f4ad8a45e01e6218c584123848c8ac66577e3084c57a42825dc32`

The next firmware image must rebuild BusyBox with this source fix or explicitly
integrate the validated binary. Reusing the old rootfs BusyBox would retain the
bug even with this source commit. Full-image packaging and size checks remain
required; no new firmware image was built or flashed for this fix.

## Live deployment and recovery

`apply-live.sh` documents the actual reversible deployment. It checks exact
BusyBox, rc, libc and loader hashes for the validated leon10 runtime, copies
the replacement from `/jffs/leon-busybox-time64/` to RAM, and bind mounts it over
`/usr/bin/busybox`. Different firmware is skipped. The live binaries are saved
on the DGX and router; they are not included in this source checkpoint.

The existing `/jffs/scripts/local-mount` hook invokes this guarded script.
Undo, original-hash restoration, hook reapplication and idempotent application
were verified. A complete router reboot was not tested. To disable and undo:

```sh
touch /jffs/leon-busybox-time64/disabled
/bin/bash /jffs/leon-busybox-time64/apply-live.sh undo
```

No boot metadata was changed. The running slot 1 remains uncommitted, and
slot 2 remains the committed fallback selected for a normal reboot.

SHA-1 ELF Build ID in `result.json` identifies the binary; it is not a
cryptographic signature. Private diagnostic logs and credentials are excluded.
