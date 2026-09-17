# GT-BE98 leon10 platform and web release

This release combines the previously validated 23-service platform split with
the dashboard and AiMesh fixes from source commit
`bccac27b3924dc4687def0600e66d67e88d6fd8e`. The copied production root differs
from the leon9 platform candidate in exactly five paths: rc, httpd, libshared,
the processed AiMesh topology page and release metadata. No test fixtures are
installed in the production root.

The libshared fix removes a null-pointer subtraction in physical-radio traffic
reporting. The HTTPD/rc build preserves the existing vendor AiMesh time32 shared
table while retaining application time64, and uses the GT-BE98 networkmap table
layout. Both MAC JSON formatters use the remaining buffer size. The translated
topology page initializes its asynchronous client list as an array. Actual
source and retained objects are in the dashboard and AiMesh checkpoints; their
canonical source changes are already published in the repository.

## Reproduction and gates

Copy `systemd-rc-platform-20260917/build/production-rootfs` with symlinks
preserved. Apply the dashboard and AiMesh `stage-next-root.py` scripts, then
set the version in `usr/share/leon-upstream.json` to
`3006.102.9-beta1-leon10` and record the source commit. The complete file delta
is in `evidence/staging-delta.json`.

Run `scripts/measure.py ROOT platform-release --zstd157`. This uses SquashFS
zstd level 22, 1 MiB blocks, tail ends and the established file-family sort.
Set `configs/packaging-policy.json` to the verified input hashes, then run
`scripts/pack-rootfs.py` with the old leon9 package and the public key.
Only the rootfs payload changes; the existing signed bootfs, kernel #36,
182 modules and trial bootguard remain unchanged. No loader update is selected.

`scripts/test-closure.py` unpacks the exact SquashFS, compares every file mode,
content and symlink, and boots the actual #36 kernel in offline QEMU. It checks
335 native/ARMEL loader closures without USB and five ABI runtime sets before
and after simulated USB mounting and ldconfig. The six platform suites and
the subsequent combined-fix rc regression remain recorded in their original
checkpoints; these runs are referenced, not claimed to have been repeated here.
Run `scripts/verify-release.py` before physical flashing.

## Size and rollback

- Image: 90,709,068 bytes; SHA-256
  `a238490efef12fdee0b2ba4780b2f2dd34eba338edd90e2a82b43746df6e697d`.
- Rootfs: 78,290,944 bytes; SHA-256
  `138479b215627bfc69e53e5bf0d1bdbeb434363af93790ccde22998d281baf6f`.
- Observed slot budget: 734 LEBs; reservations are 107 bootfs + 625 rootfs.
  Two LEBs remain, corresponding to 274,432 bytes of further rootfs growth
  before the current capacity limit, including the flasher's reserves.
- Flash only inactive slot1 after booting the committed slot2 fallback.
  Validate the written payloads, fallback volumes and bootloader hashes.
  Set `BOOT_SET_PART1_IMAGE_ONCE` only after those checks pass.
- A healthy trial may be accepted in RAM to stop its 900-second watchdog.
  This does not commit firmware. Slot1 must remain commit=0, slot2 commit=1.

The preflash archive is backed up on DGX and ML350 with an identical hash.
See `result.json` and `flash/evidence` for the actual physical outcome; this
document does not substitute for those records.

## Physical outcome

Successfully flashed slot1 and accepted the trial in RAM; slot1 commit=0 and
slot2 commit=1. Web/API, existing two-node AiMesh topology, four radios, 20
service cgroup owners, hardware flow counter progress, ASUS HTTPD restart
notifications, USB Btrfs read/write, syslog and Docker DNS/HTTP/HTTPS/LAN port
checks passed. No failure units remained. One acsd2 initialization restart
was observed and did not recur during the checks; its cause remains a
follow-up item in KNOWN-ISSUE-acsd-startup.json. This is not a firmware commit
or a claim that every printer, SMB, hotplug, roaming or pairing case was tested.
