# Docker 29.8 on the existing USB filesystem

The deployed layout is `/jffs/docker/{bin,config,data,logs}`, with `/jffs`
bound to the Btrfs USB filesystem. The host's readonly root has no `/run`.
`docker-root-view.c` gives dockerd a private mount namespace and tmpfs root
with `/run -> var/run`, then chroots and execs the ordinary daemon. `/var`
is bound non-recursively because it contains the new root view. Host
services retain their original mounts, root and network namespace.

Sources/settings here match the deployed #35/#36 helpers.
[trial/build-helpers.py](../trial/build-helpers.py) builds this helper with
the pinned external AArch64 SDK. Its older glibc ABI is compatible with
the firmware glibc 2.44 layer. Install the output at `/jffs/docker/bin/docker-root-view`, and install
`start.bash`, `stop.bash`, and `config/daemon.json` under `/jffs/docker`.
Scripts use the firmware's `/usr/bin/bash`. Keep helper binaries/scripts
root-owned and writable only by the administrator. The startup version
guards intentionally accept only the tested 4.19.294 #35/#36 builds.

Official static AArch64 archive used:
[docker-29.8.0.tgz](https://download.docker.com/linux/static/stable/aarch64/docker-29.8.0.tgz)

SHA-256: `1462a696be6029bd478d7d60d7f3c31cdd15affd1178a4a278aaf4a1d1b7f8b5`.
It contains containerd 2.3.4, runc 1.5.1 and docker-init 0.19.0.
Extract the archive's `docker/*` binaries into the deployment `bin/`.
The `/opt/bin/docker`, `docker-start`, and `docker-stop` convenience
entries point to this installation. No boot autostart was added.

Start manually with `/jffs/docker/start.bash`. It validates daemon.json,
loads exportfs before overlay, mounts the verified cgroup v1 controllers,
and enables hierarchical memory accounting when available. Stop with
`/jffs/docker/stop.bash`; it verifies the PID executable before sending
SIGTERM. Preserve any existing installation before replacing these files.

The daemon exposes a local Unix socket only, uses overlay2 on Btrfs, and
does not configure a bridge, iptables/ip6tables, forwarding, masquerading
or a userland proxy. Use `--network none` for the validated setup:

```sh
docker run --rm --network none --memory 64m --memory-swap 64m \
  --pids-limit 32 hello-world:latest
```

Memory limits require #36. Equal memory/memory-swap values prohibit
container swap; memory-swap is the combined RAM+swap limit. #35 has no
memory controller even though its basic Docker smoke tests passed.
The saved tests do not establish CPU quota, block I/O limits, rootless
operation or container networking. Before adding networking, remeasure
Runner state and hardware counters, not merely Linux forwarding flags.
