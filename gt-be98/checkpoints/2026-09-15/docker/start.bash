#!/usr/bin/bash
set -eu
umask 077
export PATH=/jffs/docker/bin:/usr/bin:/usr/sbin:/bin:/sbin:/opt/bin:/opt/sbin
case "$(uname -v)" in '#35 '*|'#36 '*) ;; *) echo 'Docker trial requires verified firmware #35 or #36; refusing on rollback firmware.' >&2; exit 90;; esac
awk '$2=="/jffs" && $3=="btrfs"{ok=1}END{exit !ok}' /proc/mounts
test "$(id -u)" = 0
if [ -S /var/run/docker.sock ]; then
  echo 'Docker socket already exists; inspect running daemon before starting another.' >&2
  exit 91
fi
/jffs/docker/bin/dockerd --validate --config-file=/jffs/docker/config/daemon.json
if ! awk '$NF=="overlay"{ok=1}END{exit !ok}' /proc/filesystems; then
  if ! awk '$1=="exportfs"{ok=1}END{exit !ok}' /proc/modules; then
    /sbin/insmod /lib/modules/4.19.294/kernel/fs/exportfs/exportfs.ko
  fi
  /sbin/insmod /lib/modules/4.19.294/kernel/fs/overlayfs/overlay.ko
fi
if ! awk '$2=="/sys/fs/cgroup"{ok=1}END{exit !ok}' /proc/mounts; then
  mount -t tmpfs -o mode=755,size=1m,nosuid,nodev,noexec leon-docker-cgroups /sys/fs/cgroup
fi
controllers='cpuacct devices freezer pids'
if awk '$1=="memory" && $4==1{ok=1}END{exit !ok}' /proc/cgroups; then
  controllers="$controllers memory"
fi
for controller in $controllers; do
  if ! awk -v c="$controller" '$1==c && $4==1{ok=1}END{exit !ok}' /proc/cgroups; then
    printf 'Required trial controller absent: %s\n' "$controller" >&2
    exit 92
  fi
  if ! awk -v p="/sys/fs/cgroup/$controller" '$2==p && $3=="cgroup"{ok=1}END{exit !ok}' /proc/mounts; then
    mkdir -p "/sys/fs/cgroup/$controller"
    mount -t cgroup -o "nosuid,nodev,noexec,$controller" cgroup "/sys/fs/cgroup/$controller"
  fi
done
if [ -e /sys/fs/cgroup/memory/memory.use_hierarchy ]; then
  if [ "$(cat /sys/fs/cgroup/memory/memory.use_hierarchy)" != 1 ]; then
    echo 1 > /sys/fs/cgroup/memory/memory.use_hierarchy
  fi
fi
mkdir -p /var/run/leon-docker /jffs/docker/logs
nohup /jffs/docker/bin/docker-root-view --daemon >>/jffs/docker/logs/dockerd.log 2>&1 </dev/null &
launch_pid=$!
printf 'DOCKER_LAUNCH_PID=%s\n' "$launch_pid"
for ((attempt=0; attempt<30; attempt++)); do
  if docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
    printf 'DOCKER_READY\n'
    exit 0
  fi
  if ! kill -0 "$launch_pid" 2>/dev/null; then
    tail -20 /jffs/docker/logs/dockerd.log >&2
    exit 93
  fi
  sleep 1
done
printf 'Docker readiness timed out; inspect /jffs/docker/logs/dockerd.log\n' >&2
exit 94
