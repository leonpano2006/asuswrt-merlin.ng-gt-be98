# GT-BE98 armel multiarch hardware trial

The armel multiarch/GCC 15 candidate was packaged, written to inactive slot 1,
read back, and booted once on the physical GT-BE98 on 2026-09-15 UTC
(2026-09-16 Europe/Zurich). The trial passed the checks below. It remains
**uncommitted**: slot 1 commit=0, slot 2 commit=1, sequences 47/46. The running
kernel is #36; the normal reboot destination is the preserved #35 in slot 2.
No firmware commit or systemd installation was performed.

## Image and rollback

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `GT-BE98_leon36-armel-multiarch-gcc15_zstd22.pkgtb` | 88,222,796 | `d20e532d4dab0777761007a967da3d897d0fa2ea3fab9fdc4b304e89f00cc364` |
| SquashFS rootfs | 75,804,672 | `9d13b0b5789843e691cf08f2083c189dbc61f48eeb5d433795183e455b4aa026` |
| Preserved signed bootfs | 12,417,164 | `2a7c327db1a185d17ba5f7b72097abf6b6158e6f2810ed7a26873144a4a8f10f` |

Rootfs uses zstd level 22, 512 KiB blocks and root ownership. The existing
kernel remains lzo-compressed inside the unchanged signed bootfs. The packer
verifies its RSA-PSS signature and exact #36 kernel hash. No loader payload
is selected. UBI reservation is 107 bootfs blocks plus 606 rootfs blocks,
leaving 21 free blocks of 126,976 bytes after flashing.

Both fallback volume hashes and the physical bootloader hash were checked
before and after flashing and again after trial boot. They are unchanged.
The full new rootfs readback and bootfs hash match the package. PID 1 is
`/usr/sbin/rc` with the existing metadata-write guard; httpd, dropbear and
watchdog do not inherit that guard.

## Physical checks

- All 312 dynamic executable dependency checks passed on the router.
- armel, armhf and aarch64 ABI probes report glibc 2.44. The four rebuilt
  libraries pass compression, XML, JSON and capability probes, and dladdr
  resolves them from `/usr/lib/arm-linux-gnueabi`.
- `/bin`, `/sbin`, `/lib`, `/run`, `/media`, `/srv`, loader entry points and
  ld.so.conf.d fragments match the candidate layout.
- Authenticated Web UI login, Dashboard client/traffic updates and System
  Information CPU/memory/connections/radio data work. The NVRAM getter fix
  is mapped from the rootfs's canonical armel library, without a USB bind
  overlay. A browser screenshot was also visually inspected.
- All four radios report up. The loaded module set is unchanged at 88;
  taint remains 4097 (P and O). All 182 packaged modules were already proven
  bytewise identical in offline validation.
- Runner remains enabled in L2/L3 mode. Over 20 seconds, aggregate L2 hardware
  hits increased from 307,178 to 322,720 and bytes from 222,275,090 to
  238,713,353. Runner flow failures and command errors were zero. This is an
  activity/error observation, not a 2.5/10 Gb/s throughput benchmark.
- Docker 29.8.0 runs from USB `/usr/local`. Default bridge DNS/HTTP, container
  package downloads and HTTPS (HTTP 200, certificate verification result 0)
  pass. A custom network passes service-name DNS, container HTTP and external
  DNS/HTTP. The test HTTP server's published LAN port was reached from DGX.
  Test containers used memory, memory+swap and PID limits. `br_netfilter`
  remains unloaded. Test containers, network and temporary probe files were
  removed; Docker was left running without adding autostart.
- All 18 saved startup hook/configuration files retain their hashes. USB
  `/usr/local` came up on fallback #35 and the new #36. Docker was tested on
  #36, not started for a separate #35 Docker test. OpenVPN server 1 restored
  automatically (state 2, errno 0, tun21).
- The trial boot logger completed at 306.247 seconds. No kernel/userspace
  fault matches were found in the trial boot log or dmesg. This is a boot and
  functional test, not a long-duration stability or WAN IPv6 qualification.

## Investigated differences

The post-reboot network snapshot is not bytewise identical to the immediate
preflash runtime. VLAN 52 and its guest bridge return at cold boot; interface
membership exactly matches the previously validated #36 cold-boot snapshot,
and the current `lan1_ifnames` setting includes those interfaces. It was not
changed to reproduce the earlier flattened runtime.

IPv6 rules and forwarding match. The IPv4 rules differ only by the absence
of four duplicate LAN-to-LAN MASQUERADE entries and twelve empty, unreferenced
NWFF/URLFF/URLFI chains. All remaining rules/policies, including Docker rules,
are identical. The original baseline hash was reproduced from the saved
rules before comparing; see `evidence/network-comparison.json`.

The initial custom-network test incorrectly assumed Alpine 3.23 provided a
BusyBox httpd applet. Its test server exited and therefore could not resolve
by service name. The default-network DNS/HTTP/HTTPS phase had already passed.
The failed test resources were cleaned, the server changed to the cached
`busybox:1.37.0` image with httpd, and the complete custom-network/LAN-port
phase passed. The successful log also contains a harmless broken-pipe line
from an early-exiting grep applet check; the saved script now consumes the
whole applet listing. This was a test harness correction, not a firmware fix.

## Recorded procedure and inputs

These scripts are the exact-input, device-state-specific procedure for this
trial. They are not an unattended installer. Their original preconditions no
longer describe the now-booted trial; do not weaken the checks to replay them.

1. Save current network/module state and the existing hooks/configuration.
   Verify fallback and physical loader hashes. Back up the package to ML350.
2. Use `return-to-fallback.sh` from the old uncommitted #36 slot 1 to stop the
   idle Docker daemon and reboot normally into the committed #35 slot 2.
3. Copy the exact package to `/tmp/leon36-armel-multiarch-gcc15.pkgtb` and run
   `flash-slot1.sh` on #35. It checks identity, active slot, sequences, UBI
   capacity, fallback hashes, physical loader hash, package hash and Runner
   state before invoking the native `bcm_flasher`.
4. Run `verify-written.sh`. After every check passes, `arm-once.sh` sets
   `BOOT_SET_PART1_IMAGE_ONCE` with `bcm_bootstate 6` and reboots.
5. Run `live-verify.bash`, then `verify-multiarch.bash` with the library probe,
   three ABI probes, library hashes and 312 executable/loader pairs staged
   at `/tmp/leon-armel-verify`. These inputs derive from the parent checkpoint
   and the pinned `manifest.json` external test inputs.
6. Start the existing USB Docker service, run `docker-network.bash`, check
   the printed LAN test port from another LAN machine, then remove only the
   labelled test server/network. Observe Runner and compare network/modules.
   Inspect Web UI and boot logs; preserve commit flags and user configuration.

The packer requires Python 3, OpenSSL and lzop. Example on the build host:

```sh
python3 scripts/pack-rootfs.py \
  --original /path/to/GT-BE98_leon36-usrmerge-run_zstd22.pkgtb \
  --rootfs ../build/rootfs.squashfs \
  --public-key saved-inputs/fit-public.pem \
  --available-blocks 734 \
  --output GT-BE98_leon36-armel-multiarch-gcc15_zstd22.pkgtb
```

734 was the measured capacity available to the replaced slot: 21 free plus
its existing 107+606 reservations. It must be freshly checked for any future
write. The old package and new rootfs must match the packer's pinned hashes.
Compilation and packaging ran on DGX; no compiler workload ran on the router.

The own-repository checkpoint stores scripts, public key, manifests and
selected verification evidence. Complete firmware, raw local-network/boot
records and the private hook/configuration archive are kept in the verified
ML350 backup, outside the public Git checkpoint. The previous offline and
preflash backups are retained separately.
