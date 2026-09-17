# NTP and mDNS ownership

This continues the hardware-tested systemd 257.13 / full less 704 image. Only
six production paths change: rc, its service-owner guard, a small argv executor,
two service units and the version metadata. No kernel, driver, acceleration,
firewall, DHCP/DNS, storage, bootguard or other daemon binary is replaced.

| Component | Configuration and policy | Process supervisor |
| --- | --- | --- |
| Avahi mDNS | Original rc configuration, service XML, custom config/postconf hooks, startup point and Time Machine refresh logic | `asus-mdns.service`, real foreground Avahi, original privilege drop and syslog output |
| NTP | Original rc peer selection, optional LAN listener/interface, WAN start/stop and clock-ready state | `asus-ntpd.service`, real BusyBox `ntp -n`, original trust and callback arguments |
| NTP synchronization effects | A `step` callback queues `start_ntpd_synced`; the rc manager runs the original DDNS/VPN/timezone work once | Remains in the rc manager's service; NTP stop cannot drain these descendants |
| USB / Time Machine mDNS updates | Non-manager callers notify rc; `start_mdns_refresh` retains the existing fast XML-refresh path | No second Avahi launcher or supervisor |
| haveged, cron, infosvr | Previous checkpoint | Existing separate systemd units |

The two units are started synchronously by rc, possibly before its READY
notification. They must not depend on `After=asus-rc.service`. `PartOf` propagates
manager stop/restart, and mount dependencies keep RAM state available until
daemon stop. Units restart unexpected exits with a bounded start rate. The
pre-start guard refuses an externally owned process and never kills it.

`Type=exec` confirms the executor was started, not DNS publication or clock
synchronization. The executor replaces itself with the real daemon, preserving
its PID. Hardware trials must separately check LAN discovery and NTP operation.

rc writes a root-only, NUL-delimited argument snapshot atomically beneath the
broker's private RAM directory. The executor accepts only the two fixed daemon
paths, bounded argument files and foreground operation. Arguments never pass
through a shell or systemd word expansion. Automatic restarts reuse the last rc
snapshot; an ASUS `service restart_ntpd` or `service restart_mdns` also regenerates
configuration. Managed errors do not fall through to legacy launch or killall.
The original legacy-init paths remain available.

The rc notification handler consumes a single NVRAM command slot. When handling
the NTP step in the manager, Stubby and disk-monitor refreshes therefore call
their original stop/start functions directly instead of queuing a nested event
that the current handler could erase. DNSSEC signalling, DDNS, VPN and other
original synchronization actions remain intact.

The tests run real rc entry-point objects, real production units, Avahi, BusyBox
NTP and the native executor. NVRAM, custom hooks and downstream service side
effects are explicit stubs; the tests do not initialize Broadcom hardware.
The fixture creates the nobody account/group and mirrors init.c's umask(0),
which the ordinary hardware stub previously omitted. No host NIC, disk or clock
is exposed to QEMU. Loopback-only NTP peers cannot prove Internet synchronization.

Before flashing: re-read free UBI space and both slot sizes, retain the committed
slot 2 / #35, flash only from the fallback into inactive slot 1, verify readback,
and arm a single boot. Do not reuse the preceding image's hardcoded flash hashes.
Do not firmware-commit this candidate before physical validation.
