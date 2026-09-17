# GT-BE98 leon8: systemd supervision for SSH

Offline-validated candidate, **not flashed or firmware-committed**. The router
continues running the previously tested leon7. Parent Git commit:
`ce06ad849356239c49e5753ec33b1bcf2346ebe2` on our
`gt-be98-systemd257-services` branch.

ASUS `start_sshd()` still prepares host keys, authorized keys, the listen port,
password-login policy, forwarding policy and receive window. Under the managed
init, it starts `asus-sshd.service`; Dropbear runs in the foreground (`-F`) in
its own cgroup. Repeated starts keep the existing main process. ASUS setting
changes continue through its stop/start path. `stop_sshd()` stops that unit and
its sessions. A main-process failure restarts the server and drains its old
cgroup. Explicit stops do not restart it.

Legacy init retains the original daemonized launch. Fork children still notify
the rc manager. A failed systemd request never falls back to a second daemon.
The root-owned argument file is atomic, private, bounded and opened without
following symlinks. An existing external Dropbear prevents a duplicate launch;
the guard never kills it. Unit startup can occur before rc reports READY, and
PartOf propagates rc shutdown. JFFS mount ordering preserves persistent keys.

The production delta contains exactly five paths: rc, the fixed-argument
executor, the ownership guard, the new unit and firmware metadata. Existing
systemd 257.13, all its leon7 feature flags, Dropbear itself, libc, ARMHF USB
layout, bootguard, bootloader, kernel #36 and all 182 modules are unchanged.
Consequently `systemctl --version` still reports `257.13-gt-be98-leon7`; the
firmware metadata identifies this candidate as leon8.

## Build and dependency boundary

`src/ssh.c`, `rc-services.c` and `rc-services.h` are the actual rc changes and
are also published at `release/src/router/rc/`. The executor and unit sources,
build/packing scripts, test sources and receipts are included in this checkpoint.
Compilation occurred on DGX, never on the router. ARMEL rc uses the recorded
GCC 15.2 flags; the native executor uses GCC 16.2, both targeting Cortex-A53
with CRC/crypto and glibc 2.44. ELF GNU build IDs are in `evidence/build-ids.txt`.

This is an incremental BSP build, not a standalone clean SDK. `build-rc.py`
reuses the exact previous mDNS/NTP object set and the fixed IPsec object.
`evidence/rc-build.json` records complete commands and retained-object hashes.
`evidence/external-inputs.json` records 159 external inputs, copied into the
private backup's `saved-inputs/dependencies`. Compiler toolchains remain in
their own existing project/backups, not in this firmware Git repository.
The inherited checkpoints listed in that manifest are required for replay.
The shared source tree and the ML350 build worktree were not edited.

Replay within the restored workspace:

1. `python3 scripts/build-rc.py`
2. `python3 scripts/prepare-root.py`
3. `python3 scripts/pack-rehearsal.py --revision ssh-v2`
4. Run `scripts/run-qemu.py` against `Image36` with the default target and
   `--target services`, `--target network_services`, `--target ssh_services`.
5. `python3 scripts/measure.py build/production-rootfs sshd-final --zstd157`
6. `python3 scripts/test-closure.py`, then pack using `scripts/pack-rootfs.py`
   and `configs/packaging-policy.json`; finally `scripts/verify-release.py`.

Use fresh output directories for replay. Exact original invocations, input
hashes and output hashes are recorded in JSON receipts. Private backups retain
the prepared rootfs image and both test guests.

## Verification

Offline Cortex-A53 QEMU uses the actual kernel #36, no NIC, host disk or hardware
passthrough. The lab changes only ASUS hardware backends and adds test files;
every production path is byte/mode/link identical to the packaged root.

- Real Dropbear key generation, public-key login and command execution over
  loopback; persistent host keys survive repeated starts and configuration changes.
- Disabled/invalid-port policies, legacy launch and child-to-manager routing.
- Start before rc READY, strict/permissive argv, port changes and crash recovery.
- Session processes belong to the SSH cgroup and disappear on explicit or rc stop;
  an independent rc child survives a daemon restart.
- Outsider refusal, private argument-file checks, symlink rejection and masked
  unit failure without legacy fallback.
- Existing rc, haveged, cron, infosvr, mDNS, NTP, OpenVPN, shutdown, mount ordering,
  hybrid cgroups and leon7 userspace feature suites pass.
- Exact packed rootfs unpacks identically. All 334 native/ARMEL dynamic programs
  resolve libraries without USB. Five runtime ABI sets pass before/after ldconfig,
  with the optional ARMHF payload mounted inside the VM only.

The first SSH test exposed the missing writable JFFS mount in the lab and
successfully exercised the RAM host-key fallback before failing its persistent
key assertion. `ssh-v2` adds a tmpfs JFFS simulation and passes the complete
suite. Production files did not change between the two lab revisions.
Actual Broadcom hardware and networking still require a later physical trial.

## Package and rollback

`GT-BE98_leon36-systemd257-sshd-leon8_zstd22.pkgtb`: 90,700,876 bytes,
SHA-256 `4270e9a5ff1d04cee10b18cdd8721774fe47b4106218f93e941bb2b23310fe03`.
The zstd-22 rootfs is 78,282,752 bytes with 282,624 bytes (276 KiB) headroom.
Signed bootfs is unchanged and its RSA-PSS signature was verified. Both flasher
1 MiB reserves remain: 107 bootfs + 625 rootfs LEBs, two LEBs remaining.

Live read-only checks show slot1 running uncommitted, slot2 committed, and
sequences 47/46. No reboot, service restart, NVRAM write, firmware write or
commit was performed for this checkpoint. Before any later flash, recheck the
actual booted/inactive partition and capacity; the current running slot must
not be treated as an inactive target. Preserve the existing one-shot trial and
fallback workflow.
