# GT-BE98 Game Dashboard traffic crash

The current leon8 HTTPS server aborted after an authenticated Game Dashboard
requested `update.cgi?output=netdev`. The response stopped after the 12-byte
`netdev = {` prefix. Broadcom's `===DDD===` kernel message accompanied SIGABRT;
the router remained up and watchdog restarted httpds, explaining the disappearing
and later returning management page.

The private process-local trace maps the fortified call to `netdev_calc` in
`release/src/router/shared/misc.c:3299`. This device has `wl0 wl1 wl2 wl3` in
`wl_ifnames`. The old implementation assumes a dot, subtracts a non-null pointer
from `strchr(word, '.') == NULL`, and passes the resulting invalid length to
`snprintf` for an eight-byte buffer. Some paths also leave the unit uninitialized.
GCC 15 / glibc 2.44 FORTIFY detects this existing source defect.

The actual source fix uses the existing `get_ifname_unit` parser for both `wlN`
and `wlN.M`, validates the radio range, falls back to the configured list index
on invalid input, and bounds the description output. No memory protection is
disabled. Only `misc.o` is rebuilt and `libshared.so` is relinked against the
recorded original objects. GCC 15.2 ARMEL softfp, glibc 2.44, the Cortex-A53 CRC /
crypto target and SHA-1 build IDs are retained. The 1,459 defined dynamic symbols
and all NEEDED dependencies are unchanged. Existing HTTPD translation and IPsec
fixes are retained.

The ARM QEMU regression reproduces the old SIGABRT and passes 16 physical,
virtual, reordered and invalid-name cases with buffer canaries. An isolated
HTTPS instance on the actual router passed 20 traffic rounds. The regular
HTTPS server then passed 30 rounds, including all four radio counters, both
JavaScript and JSON traffic endpoints, the dashboard, index, system information
and menu resources. A real Chrome login restores the complete sidebar, traffic
chart. The HTTPD PIDs stay stable; four radios and hardware L2/L3
acceleration remain enabled, with no new fatal-signal/DDD entries in the checked
interval. This is a functional check, not a throughput benchmark.

The live fix is a RAM bind mount from `/tmp/leon-libshared-fixed.so` to
`/usr/lib/arm-linux-gnueabi/libshared.so`, followed by the normal rc HTTPD restart.
Existing unrelated processes keep their previous mappings. No firmware was
flashed or committed, no boot selection was changed, and no network service was
restarted. The fix disappears on reboot. Temporary diagnostic HTTPS listeners
and signal instrumentation have been stopped.

**The previously packaged leon9 image is not fixed.** Its SHA256 is
`7f81597418b3a3a3636d0f846664d3d8145c43627a9afa02a49bef46a63074be`.
Before the next flash, stage the library with `scripts/stage-next-root.py`,
repack and recheck the firmware capacity and runtime closure. Keep the signed
#36 bootfs, kernel and 182 modules unchanged. This checkpoint intentionally does
not label the old candidate as repaired or repeat its validation claims for a
new image that has not been built.

Build with `scripts/build.py`, then `scripts/test-unit-parser.py`. The parent is
source commit `61553213b844a0528f0c5436cfe30b4815d5b265`. Restore its checkpoint
layout, the upstream integration build headers, and the separately maintained
A53 toolchain/sysroot. `evidence/retained-inputs.json` identifies every retained
link object and its archived copy. Toolchains and vendor objects are excluded
from Git; the private ML350 artifact backup contains the retained objects.

`scripts/reproduce.py` accepts `--base`, `--rounds` and `--label`, prompts for the
router password without saving it, and records only page sizes/hashes. HTTPS
tests do not evaluate certificate trust. Private memory captures, credentials,
tokens, NVRAM and private keys are excluded from publication and remote backup.
The first RAM-apply script's final check mistakenly expected the source name in
`/proc/PID/maps`; the kernel reports the bind target path. A subsequent inode and
target-path check verified both live mappings; the saved script is corrected.
