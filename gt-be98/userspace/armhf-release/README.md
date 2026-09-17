# GT-BE98 leon6: fitting ARMHF USB + OpenSSL 4 release

This checkpoint builds on `armhf-usb-20260917` (Git 65bbcda3). It retains
kernel #36, signed bootfs, all kernel modules and the real Broadcom/ASUS
ARMEL dependency closure. The production root inherits leon5 mDNS/NTP
systemd ownership, the HTTPD/IPsec fixes and full less 704. Systemd stays
257.13 with its existing feature configuration.

Only the optional ARMHF directory is external, at
`/tmp/mnt/JFFS/system-libs/gt-be98/8da410f090d92cff/arm-linux-gnueabihf`.
It is not under `/usr/local`. Native AArch64 and ARMEL boot dependencies
remain internal. The USB payload must be installed before using ARMHF
programs; system boot does not depend on that payload.

Capacity: final rootfs 78,458,880 bytes versus the 78,565,376-byte limit,
leaving 106,496 bytes (104 KiB). The unmodified flasher's extra 1 MiB
allowance for EACH bootfs/rootfs is included. Slot1 requires 107+627 LEB,
734 total. No fallback volumes are reduced and no reserve is waived.
SquashFS uses zstd 1.5.7 level 22, 1 MiB blocks, tail-end packing and the
established family-name sorting. Candidate FIT is 90,877,004 bytes.

Selected size changes (versions/features unchanged):

* libstdc++ AArch64 GCC 16.2.0 and ARMEL GCC 15.2.0 rebuilt with -Oz;
  ARMEL keeps ARM instruction mode and softfp ABI. Both preserve every
  original exported symbol including symbol version, binding and data size.
* Full zstd 1.5.7 CLI uses upstream `zstd-dll` against the already shipped
  native libzstd 1.5.7 and zlib 1.3.2. Threads, gzip, dictionary training,
  benchmarks and legacy support remain enabled. No small/frugal target.
* Existing SQLite 3.42.0 CLI rebuilt -Oz/LTO, identical engine options,
  source ID and CLI help. FTS5, RTREE, JSON, WAL and transactions retained.
* Native OpenSSL 4.0.2 comes from the preceding full-feature -Oz/LTO
  checkpoint; ARM32 3.5.8 and Broadcom 1.1 remain unchanged.

All new C/C++ builds target Cortex-A53 CRC/crypto with glibc 2.44.
ELFs retain SHA1 GNU build IDs; these are identifiers, not signatures.
Signed bootfs is preserved and RSA-PSS verified during packaging.

Validation before flash: final SquashFS unpack inventory equals source;
330 executable loader closures pass without USB on exact kernel #36;
AArch64, ARMEL, ARMHF and both legacy compiler runtime/C++ probe sets pass
before/after ldconfig; exceptions across DSOs and both string ABIs pass.
Missing USB leaves native services usable. Dynamic zstd round trips with
old CLI (ultra22/threads, gzip, dictionaries), rejects corruption; SQLite
transaction/WAL/FTS/RTREE/JSON/dbstat/integrity tests match original.
Both OpenSSL major-version command paths load in QEMU. Hardware testing
and firmware flash receipts will be recorded separately in flash/evidence.

Rebuild dependencies: sibling checkpoints `a53-runtimes-20260916`,
`gcc162-usb`, `userspace-refresh-20260917`, `multiarch-loader-20260916`,
`rmerlin-integration-20260916`, `systemd-rc-next-20260917`,
`rootfs-size-20260916`, `rootfs-slim-20260917`, `armhf-usb-20260917` and
`less-full-20260917`. Compiler wrappers/sysroots are explicitly recorded
in commands JSON. Existing upstream zstd/zlib sources originally came
from `/home/leonpano/gcc16-a53/build/`; source copies are in the backup.
Run the two `build-small-cxx.py ABI --optimization oz` builds, build the
SQLite/zstd CLI, stage the parent plus runtime overlay, run feature tests,
`finalize-root.py`, `test-qemu.py`, then `pack-rootfs.py` with the policy.
Scripts do not imply every experimental build should be promoted.

Rejected experiments: whole-libstdc++ LTO fails historical .symver alias
assembly; Thumb mode and alternative file sort orders were not selected.
The first dynamic zstd build lost make target feature flags and was rejected;
`zstd-dynamic-full` alone is used. `cxx-oz-dynamic-zstd` measurement is
invalid (unstripped temporary input); see its marker. Final selection is
exclusively `evidence/final-root-changes.json` and candidate manifest.

Flash only from running committed slot2 #35 into inactive slot1. Recheck
size, USB, bootloader/fallback hashes and metadata. Verify written image,
then request PART1_IMAGE_ONCE. Do not firmware-commit. RAM acceptance
cancels only the 900-second trial watchdog after physical checks; later
reboot retains committed slot2 fallback.

## Physical trial completed 2026-09-17

Final package SHA256 is
`85be675ab95ae93cb6e52d82666e0e7c4f8cce131b4bf0a46c5dc56f25c7725b`;
rootfs SHA256 is
`4200e7ea7e5340ac0407ce18c9a1ae628c9a37d2dbef665e24ae2e566331dd9c`.
The earlier package differs only in the OpenSSL metadata label, corrected
from 4.0.0 to the actual unchanged 4.0.2. Use the current candidate manifest.

Flashed inactive slot1 while booted from committed slot2. Readback matched;
fallback bootfs/rootfs and bootloader SHA256 unchanged. Once-only boot
successfully reached leon6 #36 with systemd PID1. Four radios, OpenVPN,
core services and all five runtime probe sets passed. Both new mDNS/NTP
units are active with zero restarts, NTP synchronized, no failed units.
Authenticated web pages and the rc HTTPD restart callback passed.

L2/L3 hardware acceleration is enabled. During the observation, 79
retained flows advanced by 18,837 hardware hits / 7,898,950 bytes.
Docker DNS, HTTP/HTTPS, custom-network service discovery and host-to-LAN
published port passed. Test containers/networks were removed; Docker is
running again with no running containers, as before the maintenance.

The trial is accepted ONLY in RAM (root-owned mode 0600); firmware slot1
remains commit=0, slot2 commit=1, next normal reboot points to slot2. No
permanent firmware commit was performed. See flash/evidence/physical-receipt.json.
This is a successful bounded smoke test, not long-term stability evidence.

Published text logs have trailing spaces trimmed. Original captured output
is retained in armhf-release-complete.tar on DGX and ML350.
