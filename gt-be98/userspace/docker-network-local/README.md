# GT-BE98 Docker networking and USB /usr/local

This checkpoint completes the earlier Docker smoke-test installation on the
running #36 firmware. Containers now have ordinary IPv4 bridge networking, NAT,
DNS and published ports. Docker's executables live in USB-backed `/usr/local`.
The prior `bridge=none`, disabled iptables/forwarding/masquerade configuration was
the reason ordinary containers could not reach the network. The vendor iptables
1.4.15 also lacks the `--wait` option required by Docker 29.

## Installed layout

| Purpose | Location |
| --- | --- |
| USB prefix, bind-mounted at `/usr/local` | `/jffs/usr-local` |
| Docker, dockerd, containerd, runc and supporting binaries | `/usr/local/bin` |
| Start, stop and firewall reconciliation scripts | `/usr/local/sbin` |
| Docker-only legacy iptables 1.8.13 | `/usr/local/libexec/docker/iptables/sbin` |
| Private root view for the older #35 `/run` layout | `/usr/local/libexec/docker/docker-root-view` |
| Existing image/container/volume data | `/jffs/docker/data` |
| Configuration and logs | `/jffs/docker/config`, `/jffs/docker/logs` |
| Migration backup | `/jffs/docker/backups/network-local-20260915` |

The eight official Docker 29.8.0 binaries retain their original hashes, listed in
`configs/docker-binaries.sha256`. No Entware libraries are used. ASUS continues
to run `/usr/sbin/iptables` 1.4.15; only Docker's child-process PATH selects the
new tool. The three old `/opt/bin/docker*` links are removed. Historical
`/jffs/docker/bin`, `start.bash` and `stop.bash` paths remain compatibility links.

The existing `/usr/local/share -> /tmp/share` firmware alias is preserved. USB
mounting is restored by both copies of `post-mount` (internal UBIFS and USB),
with an idempotent `services-start` fallback. Login PATH is prepended before the
existing interactive bash handoff. Existing terminal, locale, memory, Netdata,
SSH and Web UI fix hooks are preserved. Non-login SSH commands should use the
explicit `/usr/local/bin/docker` path, because Dropbear's compiled PATH lacks
`/usr/local`.

## Network behavior

The current device is an AP: `br0=192.168.100.10/24`, gateway `192.168.100.1`.
The inspected LAN and VPN routes do not overlap the default container subnet
`172.30.98.0/24` or the user-network pool `172.31.0.0/16`, divided into /24s.
Reassess those pools if LAN/VPN addressing changes.

Docker manages its normal bridge, forwarding and NAT rules. `ip-forward-no-drop`
keeps the host's FORWARD policy intact. `userland-proxy=true` and `icc=true`
avoid requiring global bridge netfilter for these networks, so normal LAN
bridging does not enter that additional filtering path. An explicit proxy path
is required by this static Docker distribution. Do not combine an explicit
`bridge` name with `bip`, which Docker rejects. Creating networks with ICC
disabled changes the bridge-netfilter requirement and was not tested here.

Merlin's `firewall-start` and `nat-start` hooks invoke a serialized reconciliation
helper. Docker rebuilds its own rules from current network/port state. With
`live-restore=true`, containers remain running across this daemon restart. The
helper refuses recovery without live restore, does nothing when Docker is
stopped, and never flushes the vendor firewall or changes its default policy.

Docker is running now. Daemon startup remains manual, as in the earlier trial:
use `docker-start` after login, or `/usr/local/sbin/docker-start` explicitly.
`docker-stop` stops the daemon; with live restore enabled it leaves containers
running. Use `docker stop` first if the containers should stop as well. This
checkpoint adds no automatic daemon startup or router reboot.

## Reproduce and install

Dependencies are the existing official Docker 29.8.0 installation and the
verified #36 cgroup/memcg firmware, merged `/usr`, `/run`, USB JFFS and Web UI
fix checkpoint. These are runtime integration changes outside the firmware
source tree; the aarch64 Buildroot toolchain repository is not modified.

1. On the AArch64 DGX, run `bash scripts/build-native.bash`. This downloads the
   SHA-256-pinned Netfilter source and builds with GCC 13, `-mcpu=cortex-a53`,
   static libxtables/extensions/libc, and the legacy backend. It also builds the
   fallback root-view helper. Both are checked under QEMU Cortex-A53 before
   deployment. Build prerequisites include GCC 13, make, pkg-config, flex,
   bison, xz, curl, binutils and qemu-aarch64.
2. Back up the current router hooks and Docker configuration. Run
   `scripts/prepare-hooks.py --before PATH_TO_EXTRACTED_JFFS --out build` on DGX.
   It requires the inspected original hashes, including the previous Web UI fix.
   Review and merge explicitly if those hooks differ; never bypass the guards.
3. Stage `scripts/`, `configs/`, and the generated `build/` artifacts under
   `/jffs/docker/migration-network-local-20260915`. `install-live.bash` performs
   a **one-time** migration with a new backup directory and an empty container
   inventory. It refuses an existing prefix/backup. Do not rerun it on the
   already migrated router. All compilation is done on DGX.
4. Verify container DNS, HTTP/HTTPS, image pulling, custom-network service DNS,
   published ports and acceleration before running `persist-hooks.bash`.
   That script guards the original hook hashes and refuses existing firewall
   hooks rather than overwriting unrelated customizations.

The DGX's custom GCC 16.1 `libgcc` contains an unconditional LSE `casal` in
`version_lock_lock_exclusive`, which traps on B53 even when application CFLAGS
specify Cortex-A53. That runtime is **not** fixed by this checkpoint. GCC 13 was
used for the deployed helpers, and QEMU plus live execution passed. This is a
dependency issue, not evidence that GCC 16-generated Cortex-A53 code in general
is incompatible. See `install-manifest.json` for deployed hashes.

## Validation and recovery

`evidence/validation.json` records successful default-bridge DNS/HTTP, fresh
Alpine image pull, in-container package installation, HTTPS 200 with certificate
verification result 0, custom-network DNS and LAN port access. Removing only
Docker's NAT entry triggered successful recovery; the test container retained
PID 17128 and remained reachable. Test containers, custom network and port
18098 were removed afterward.

All original iptables rules/policies and the loaded module set remained intact.
FORWARD stayed ACCEPT, `br_netfilter` remained unloaded, taint stayed 4097, and
Runner hardware activation successes increased with zero activation failures.
This verifies continued acceleration activity, not a 2.5G/10G throughput result.
Only IPv4 was tested; the current uplink has no IPv6 routing. CPU quota/cpuset/
blkio controller limitations are unchanged. A full router reboot and the #35
fallback boot are not tested by this checkpoint; the fallback helper's mount
probe passes on the current firmware.

Original binaries and configuration are preserved in the USB migration backup;
the workspace also holds the original hooks and a complete compressed copy of
the new prefix. For rollback, stop application containers explicitly, stop the
daemon, and review the saved original config/hooks against any newer changes.
Do not blindly restore the historical complete iptables snapshot over later
VPN/firewall changes. The USB prefix can be retained independently of Docker
network settings. No image/volume pruning or firmware flashing is involved.

Boot state is unchanged: running partition 1 (#36, trial), committed/reboot
partition 2 (#35), sequences 47/46. The queued firmware rootfs remains unchanged;
these USB runtime files must accompany it when deploying the next candidate.

References: [Docker firewall behavior](https://docs.docker.com/engine/network/packet-filtering-firewalls/),
[Moby bridge requirements at the installed commit](https://github.com/moby/moby/blob/3ce5872/daemon/libnetwork/drivers/bridge/bridge_linux.go),
[Docker live restore](https://docs.docker.com/engine/daemon/live-restore/),
[Netfilter source and checksum](https://www.netfilter.org/projects/iptables/downloads.html).
