# ASUS service ownership after systemd 257 upgrade

The ASUS rc broker remains the hardware/legacy-service manager. The kernel, BSP,
network acceleration, Wi-Fi blobs, mdev, DHCP/DNS, firewall, Docker and OpenVPN
ownership stay as in the physical-tested RMerlin a3 parent.

| Component | Start policy | Process supervisor | Stop policy |
| --- | --- | --- | --- |
| haveged | Existing rc entry point | systemd, foreground | Existing separate service |
| cron | Existing rc entry point; restart preserves timezone refresh | systemd, real BusyBox `crond -f -l 9` | Ordinary restart/stop preserves running jobs; manager stop drains remaining jobs before storage |
| infosvr | Existing rc point and modem-bridge guard, `br0` retained | systemd, existing foreground binary | Unit cgroup stopped; `PartOf=asus-rc.service` |
| cron job cleanup | Before ASUS manager starts, oneshot stays active | systemd | Stops after manager and before its storage prerequisites |

The production units for cron and infosvr do not wait for ASUS rc READY: rc
starts them synchronously during initialization. Giving them `After=asus-rc`
would deadlock boot. The separate cron cleanup unit is already active before
rc begins and has no dependency on those daemon units.

The dispatcher uses fixed unit names, manager identity checks and child-only
wait/kill operations. It masks SIGCHLD during systemctl, clears the child signal
mask, limits the request to 30 seconds and refuses legacy fallback on a managed
error. Legacy init still uses the original launcher paths. The rc periodic
crond respawn is disabled only in managed mode, giving one restart supervisor.

`Type=exec` confirms successful exec, not application-level readiness. infosvr
has no readiness notification; LAN UDP discovery requires physical testing.
Both new units restart on any unexpected process exit and use a bounded start
limit. cron deliberately uses KillMode=process so a timezone refresh does not
terminate arbitrary scheduled jobs. Its separate cleanup uses only the known
unit cgroup and systemctl kill; it does not kill unrelated matching names.

The systemd manager, executor, tools and private shared libraries are upgraded
together. Only libsystemd-core-255.so and libsystemd-shared-255.so are removed;
the version-257 libraries use the same multiarch directory. Runtime libraries
and ELF interpreters remain from the current glibc 2.44/A53 sysroot.

The early preparation script mounts all five existing v1 controllers before
systemd starts. Unmodified upstream 257.13 follows an existing hierarchy and
adds its hybrid cgroup2 manager mount. Docker retains v1 resource/device
controls. This is a deliberate transition arrangement, not unified v2 and not
an assertion that all Podman features work.
