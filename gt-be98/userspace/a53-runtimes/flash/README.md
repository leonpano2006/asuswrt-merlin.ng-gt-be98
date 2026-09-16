# A53 runtime firmware: verified physical trial

The 89,439,308-byte `GT-BE98_leon36-a53-runtimes_zstd22.pkgtb` was written to
inactive slot 1 from committed slot 2 / kernel #35, then booted once and verified
on the GT-BE98. The router is running the new image with **slot 1 uncommitted**.
Normal reboot still selects slot 2 / #35; commit flags remain `[0, 1]`, with
sequences `[47, 46]`. No firmware commit command was issued.

Image SHA-256: `7d48c2274be8dae6179096208a738d5214b321805b6d1fa9f0736bf23eff92f9`.
Rootfs SHA-256: `68888e499d0095374266c8f2adf0be296c5370e893c81c548e7a36c1030e9216`.
The kernel remains #36. Both candidate payloads passed readback; fallback
bootfs/rootfs and the bootloader retain their original hashes. The fresh UBI
calculation leaves 12 eraseblocks after the 107 + 615 block reservations.

## Physical results

- All 244 installed library hashes match the candidate. Five current/legacy
  compiler cases pass libgcc unwind/backtrace, wide division, thread cancellation
  and exceptions across a DSO. Ten C++ tests cover both string ABIs. These execute
  through their normal ELF interpreters and load the installed multiarch libraries
  without an `LD_LIBRARY_PATH` override. ARMEL and AArch64 `ldd` both work.
- All three glibc ABIs, four rebuilt C libraries, legacy plugin consumers, 312
  cache-free executable dependency checks and 312 normal-cache checks pass.
  The 257 removed aliases remain absent; all 32 required compatibility entries
  and the Ubuntu-compatible loader search paths remain correct.
- Authenticated Web UI login, dashboard live traffic and System Information
  render correctly. Four radios are up, all 88 module names match the pre-flash
  baseline, and taint remains 4097. The PID1 metadata guard is present and is
  not inherited by httpd, dropbear or watchdog.
- Docker 29.8.0 runs from the existing USB-backed `/usr/local` bind mount.
  Default bridge DNS/HTTP/verified HTTPS, custom bridge DNS/HTTP and LAN-only
  port publishing pass. Actual memory and memory+swap limits both read 32 MiB,
  with zero memory fail count. Test containers, their network and RAM probes
  were removed. The original daemon was restarted; no autostart hook changed.
- Runner L2/L3 hardware acceleration remains enabled. After test cleanup,
  aggregate L2 hardware hits/bytes increased from 217224 / 81939013 to
  228554 / 95491364 over 20 seconds. Flow and command-list errors stayed zero.
  The separate host-IP-table IPv4 add/delete counters each increased once
  during Docker bridge testing; after cleanup they stayed at 1/1, with IPv6
  at 0/1, matching the preceding trial's values. This is not a throughput test.
- Normalized IPv4/IPv6 rules, forwarding values, interfaces/bridge membership,
  VPN state and module names match baseline. All 18 hook/config fingerprints
  match the existing private backup. No new configuration archive was exported.
- The current boot logger completed at 306.925 seconds. At the 579-second check,
  no panic, oops, loader failure, illegal instruction or OOM entry was present.
  Final cleanup reconfirmed slot 1 uncommitted and slot 2 as normal reboot target.

The USB SSD remains at 5 Gbps; this image contains no USB speed modification.

## Reproduction and evidence

`evidence/live-summary.json` summarizes the retained checks. The guarded scripts
pin this exact firmware, baseline and slot state; do not run them against a
different state without reviewing every hash and capacity requirement.
`return-to-fallback.sh`, `flash-slot1.sh`, `verify-written.sh` and `arm-once.sh`
record the complete write/one-time-boot procedure.

`prepare-hardware-probes.py --checkpoint CHECKPOINT --previous-probes PREVIOUS`
assembles already-built probes from the prior multiarch checkpoint and this
runtime build, plus a current `saved-inputs/hooks-config.sha256` fingerprint
list. Probe executables and matching gconv modules are staged only under `/tmp`;
the test bundle contains no replacement runtime library payloads.

The complete build/source/firmware base backup remains `a53-runtimes-backup.tar`,
SHA-256 `9789859663846922442a0a11057cba93738364f556e2c417544a436f3636db23`,
already verified locally and on ML350. The physical-trial checkpoint is an
additional archive and depends on that base for the original image/build inputs.
