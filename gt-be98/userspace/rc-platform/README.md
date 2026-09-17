# GT-BE98 leon9 platform service candidate

Offline-validated candidate: not flashed and not firmware-committed. Parent is the physically
validated leon8 (Git e4108078d915e8eb493973d82d41e468bf0c9cf7).

This checkpoint transfers daemon lifetime to 23 systemd units while retaining
ASUS's NVRAM policy, generated configuration, hardware initialization and ordered
calls in rc. The previously split six services remain unchanged in behavior.

| Area | New units |
| --- | --- |
| Wi-Fi userspace | eapd, acsd, acsd2, bsd, wlceventd, roamast |
| Logging | syslogd, klogd |
| Management HTTP | httpd, httpds, httpds6 |
| USB and sharing | hotplug2, lpd, u2ec, nmbd, smbd, wsdd |
| ASUS services | networkmap, notification (nt_monitor and its nt_center child), protection, netool, cfg-server, cfg-client |

The ASUS HTTP server has source (`release/src/router/httpd/httpd.c`). Its main
already stays in the foreground. No UI rewrite is necessary for this batch:
existing authenticated web actions keep calling notify_rc, and the rc handlers
now control the appropriate units. HTTP/HTTPS/WAN IPv6 are separate instances.
The prior bounds fix in ej.c and the rebuilt HTTPD binary are preserved exactly.

A native AArch64 supervisor tracks foreground, forking and double-forking vendor
programs through a subreaper and direct-child PPid checks. The current #36 kernel
has CONFIG_CHECKPOINT_RESTORE disabled, so `/proc/.../children` is unavailable;
the production helper does not depend on it. A bounded startup handoff handles
late double-forking. After startup it tracks the primary daemon, not merely the
existence of an unrelated worker. Stop and crash recovery act on the unit cgroup,
never by global killall or by adopting external PIDs. Existing external daemons
cause start failure. Separate systemd-owned HTTPS instances are allowed.

The rc bridge publishes a single atomic, root-only NUL-separated record containing
working directory, optional Samba CPU selection, timezone, PATH and literal argv.
The child also receives ASUS _eval-compatible session/signal initialization and
the zero umask established by ASUS sysinit; stdout/stderr go to the journal.
It uses a fixed service/binary table with no shell evaluation. Only the rc manager
can publish or start a service; child callers use named rc notifications. Managed
errors never fall back to starting an untracked legacy daemon. Original init
retains its legacy launch path. Units do not order After=asus-rc.service because
rc starts them synchronously before its READY notification.

Samba configuration/password generation and the BE98's existing last-CPU affinity
remain in rc. The supervisor does not parse credentials. Notification children
are cleaned up with their parent unit. Hotplug's old duplicate restart loop is
disabled under systemd; hardware coldplug, mount/unmount and driver setup stay in
rc. All units participate in asus-rc's shutdown via PartOf.

## Boundaries

This is a substantial daemon split, not removal of all ASUS rc logic. Broadcom
hostapd configuration/start/stop still comes from retained `hostapd_config_be.o`;
its source is absent and the SDK Makefile explicitly supports a prebuilt fallback.
Its bytes are not modified. Radio/driver initialization, acceleration, bridge,
VLAN, WAN, firewall and hardware watchdog policy remain on the existing paths.
ASUS USB controller/mount policy, usbmuxd/fsmd and additional AiMesh/cloud features
also remain for later dependency audits. Docker's earlier RAM-only unit is not
silently made persistent here.

## Reproduction and evidence

Build on DGX, never on the router. Use scripts/build.py, build-tests.py and
build-callpaths.py, then prepare-root.py. Original GCC 15 ARMEL compile flags and
retained link objects are recorded in evidence/rc-build.json; the native helper
uses the existing GCC 16.2 Cortex-A53/glibc 2.44 wrapper. Toolchains stay external.
Dependencies and retained object hashes are captured separately.

QEMU runs the actual #36 kernel offline with no NIC, host disks or passthrough.
Hardware-dependent daemon lifetime is tested with explicit VM-only fixtures;
this does not establish actual radio, acceleration, printer or AiMesh health.
A second VM runs the shipped logger and Samba binaries. The callpath test links
the actual services.o and usb.o; only hardware/NVRAM effects and certificate
preparation are stubbed. A copy of services.o has just the certificate-preparation
symbol weakened for the test override; production object bytes are unchanged.

The final release report below lists passing suites, exact package hashes and
capacity. Failed intermediate runs remain in the complete backup for diagnosis.
An eventual physical trial must verify radio association, acceleration counters,
authenticated web settings/restart callbacks, USB unplug/remount, actual SMB file
I/O, printer behavior where available, logs and shutdown/rollback behavior.

The original cron regression fixture had a shutdown race: its shell TERM trap
could fork echo while systemd was terminating that cgroup, and the helper echo
could also receive TERM. The new C fixture writes the same receipt directly with
async-signal-safe syscalls. The test still requires the job to survive ordinary
cron restarts, receive graceful TERM during shutdown, disappear from /proc, and
finish before storage unmount. It allows PID 1 a bounded interval to reap a zombie
after the cgroup has become empty. Production cron behavior is unchanged.

## Final release evidence

- Package: `GT-BE98_leon36-systemd257-platform-leon9_zstd22.pkgtb` (90,709,068 bytes).
- Package SHA-256: `7f81597418b3a3a3636d0f846664d3d8145c43627a9afa02a49bef46a63074be`.
- Rootfs: 78,290,944 bytes, zstd level 22, 1 MiB blocks, 268 KiB headroom.
- Flasher reservations: 107 bootfs + 625 rootfs LEBs; two remaining LEBs.
- Original signed bootfs/kernel #36, all 182 modules and trial bootguard unchanged.
- 335 executable loader checks without USB; five ABI sets with and without cache.
- Six final QEMU suites use `platform-v7/guest.cpio.gz` with byte-identical production files.
- Source patch applies exactly to its saved base; 244 dependency files hashed and saved.

| Final suite | Seconds | Result |
| --- | ---: | --- |
| release-default | 147.86 | Pass |
| release-platform | 142.19 | Pass |
| release-real | 51.12 | Pass |
| release-services | 96.53 | Pass |
| release-network | 67.35 | Pass |
| release-ssh | 63.88 | Pass |

Router access in this checkpoint was read-only (status, process paths and UBI capacity).
No live daemon restart, flash write, reboot or firmware commit was performed.
