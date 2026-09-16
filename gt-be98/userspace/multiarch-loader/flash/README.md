# Ubuntu multiarch physical trial — 2026-09-16

The 88,333,388-byte `GT-BE98_leon36-ubuntu-multiarch_zstd22.pkgtb` was
flashed to inactive slot 1 while committed slot 2 / kernel #35 was running.
The router booted this exact candidate successfully, and remains **uncommitted**.
Normal reboot still selects #35 in slot 2; commit flags are `[0, 1]` and
sequences remain `[47, 46]`. The bootloader and both fallback volume hashes
are unchanged. No firmware commit command was used.

## Physical verification

- Fresh UBI capacity: 734 replaceable blocks, new reservations 107+607,
  remaining 20. PKGTB transfer hash and complete bootfs/rootfs readbacks match.
- All 62 new glibc runtime/loader files match their packaged hashes.
  All three ABI paths and `$LIB` expansions match the extracted Ubuntu reference.
- 257 flat armel aliases are absent and all 32 documented compatibility entries
  resolve. Each of 312 executable dependency checks passes both without cache
  and with the normal cache; the device's cache was never deleted for testing.
- AArch64, armel and armhf glibc 2.44 tests pass memory/allocator, pthread/TLS,
  libm, kernel/resolver and matching staged gconv checks. The gconv test modules
  are temporary files under `/tmp`, not an installation or firmware change.
- Four rebuilt-library functional tests and existing lighttpd, iptables and
  strongSwan plugin consumers pass.
- Authenticated Web UI login, live dashboard data and System Information work.
  Four radios are up; all 88 loaded module names match baseline; taint is 4097.
- USB `/usr/local` Docker 29.8.0 passes default DNS/HTTP/verified HTTPS, custom
  DNS/HTTP and LAN-only port publishing. Actual cgroup memory and memory+swap
  limits both read 32 MiB, with zero memory fail count. Test containers and
  network were removed. Docker is running as before; no autostart hook changed.
- Runner L2/L3 hardware acceleration remains enabled. Over the 20-second sample,
  active L2 hardware counters increase from 132846 hits / 49366170 bytes to
  135354 hits / 50268292 bytes. Runner flow and command-list errors remain zero.
  The separate host-IP table counters (IPv4 add/delete: 1/1; IPv6 add/delete: 0/1)
  do not increase during the sample. This is observation, not a speed benchmark.
- Normalized IPv4/IPv6 rules, forwarding values, interface/bridge membership,
  VPN state and loaded module names match the pre-flash baseline exactly.
  All 18 startup/config file hashes are unchanged; `br_netfilter` is not loaded.
- The current boot logger finishes at 306.464 seconds. Current boot and dmesg
  contain no panic, oops or loader error. Old #32 panic entries belong to earlier
  boots in the cumulative diagnostic log and are retained separately in backup.

The private cumulative log, dmesg, hook/config archive and probe binaries are
kept in the separate ML350 hardware backup. The original full source/build/
firmware backup remains `multiarch-loader-backup.tar`, SHA256
`5abd6984235c0e509b377b1e7b49496624a2d500491bb2d3399f81c255c9f31d`.

## Recorded procedure and code

The scripts pin this trial's exact baseline, image hashes, kernel and partition
state. They intentionally refuse a different state; do not reuse them blindly.
`return-to-fallback.sh` first guarded the old slot-1 trial and returned normally
to #35. `flash-slot1.sh` wrote only inactive slot 1; `verify-written.sh` checked
all new/fallback/bootloader hashes. `arm-once.sh` set only `bcm_bootstate 6` before
reboot. `live-verify.bash`, `verify-multiarch.bash`, `docker-network.bash`,
`acceleration-observe.bash` and `final-state.bash` produced the physical checks.

`prepare-live-probes.py` assembles already-built probes and exact expected
runtime/alias/loader manifests from this and the previous armel checkpoint.
It requires a fresh private hook/config hash list in `saved-inputs/` and the
staged matching gconv modules; its resulting archive is extracted only to RAM.
No compilation was performed on the router.

The final cleanup's informational `readlink /usr/local` returned nonzero because
this prefix is a USB **bind mount**, not a symlink. The actual Docker/memcg checks
and container cleanup had already passed. The final verification uses mountinfo
and confirms that bind mount; dependent network comparison was then completed.
