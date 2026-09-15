#!/usr/bin/bash
set -eu
export PATH=/jffs/docker/bin:/usr/bin:/usr/sbin:/bin:/sbin:/opt/bin:/opt/sbin
date -u
uname -a
case "$(uname -v)" in '#36 '*) ;; *) exit 90;; esac
grep -q 'root=/dev/ubiblock0_4' /proc/cmdline
bcm_bootstate
zcat /proc/config.gz | grep -E '^(CONFIG_(MEMCG|PAGE_COUNTER|GTBE98_MEMCG_ABI|GTBE98_CGROUP_ABI|BTRFS_FS_POSIX_ACL)=|CONFIG_MEMCG_SWAP|# CONFIG_MEMCG_KMEM)'
cat /proc/cgroups
awk '/^(MemTotal|MemAvailable|SwapTotal|SwapFree):/{print}' /proc/meminfo
/jffs/docker/start.bash
docker version --format 'Client={{.Client.Version}} Server={{.Server.Version}}'
docker info --format 'MemoryLimit={{.MemoryLimit}} SwapLimit={{.SwapLimit}} OomKillDisable={{.OomKillDisable}} CgroupVersion={{.CgroupVersion}} Driver={{.Driver}}'
docker run --rm --network none --memory 32m --memory-swap 32m --pids-limit 32 --cap-drop ALL --security-opt no-new-privileges busybox:1.37.0 sh -ec '
  test "$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes)" = 33554432
  test "$(cat /sys/fs/cgroup/memory/memory.memsw.limit_in_bytes)" = 33554432
  test "$(cat /sys/fs/cgroup/pids/pids.max)" = 32
  grep -Eq "^Seccomp:[[:space:]]+2$" /proc/self/status
  dd if=/dev/zero of=/memory-probe bs=1048576 count=8
  sync
  usage=$(cat /sys/fs/cgroup/memory/memory.usage_in_bytes)
  echo LIVE36_MEMORY_USAGE=$usage
  test "$usage" -ge 8388608
  test "$usage" -lt 33554432
  cat /sys/fs/cgroup/memory/memory.stat
  rm /memory-probe
  echo LIVE36_MEMORY_LIMITS_AND_PAGECACHE_PASS
'
docker run --rm --network none --memory 32m --memory-swap 32m --pids-limit 32 hello-world:latest
test -z "$(docker ps -aq)"
echo LIVE36_CONTAINERS_CLEANED
cat /proc/cgroups
/bin/fc status
cat /proc/pktrunner/accel0/stats
printf 'FAULT_COUNT='
dmesg | awk '/Kernel panic|Internal error|BUG:|Oops:|WARNING: CPU:|Out of memory:|Memory cgroup out of memory:/{n++}END{print n+0}'
printf 'TAINT='; cat /proc/sys/kernel/tainted
bcm_bootstate
