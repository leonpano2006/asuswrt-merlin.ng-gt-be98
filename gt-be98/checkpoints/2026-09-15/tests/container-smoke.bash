#!/usr/bin/bash
set -eu
export PATH=/jffs/docker/bin:/usr/bin:/usr/sbin:/bin:/sbin:/opt/bin:/opt/sbin
volume=leon-docker-smoke-20260915
if docker volume inspect "$volume" >/dev/null 2>&1; then
  test "$(docker volume inspect "$volume" --format '{{index .Labels "leon.test"}}')" = installation
else
  docker volume create --label leon.test=installation "$volume"
fi
docker pull busybox:1.37.0
docker run --rm --name leon-docker-smoke-write --network none --pids-limit 32 --read-only --cap-drop ALL --security-opt no-new-privileges=true --env "LEON_HOST_NETNS=$(readlink /proc/1/ns/net)" --mount "type=volume,source=$volume,target=/proof" busybox:1.37.0 sh -ec '
  test "$(awk "/^Seccomp:/{print \$2}" /proc/self/status)" = 2
  test "$(awk "/^NoNewPrivs:/{print \$2}" /proc/self/status)" = 1
  test "$(readlink /proc/self/ns/net)" != "$LEON_HOST_NETNS"
  # This BSP creates down tunnel fallback devices in each new net namespace.
  # Require no active non-loopback interface and no IPv4 routes.
  for dev in /sys/class/net/*; do
    test -d "$dev" || continue
    test "${dev##*/}" != lo || continue
    flags=$(cat "$dev/flags")
    test "$((flags & 1))" -eq 0
  done
  test "$(awk "NR>1{n++}END{print n+0}" /proc/net/route)" = 0
  test "$(cat /sys/fs/cgroup/pids/pids.max)" = 32
  printf "leon-docker35-persistence\n" > /proof/value
  printf "PASS seccomp_no_new_privileges_network_none_pids32_volume_write\n"
'
docker run --rm --name leon-docker-smoke-read --network none --pids-limit 32 --read-only --cap-drop ALL --security-opt no-new-privileges=true --mount "type=volume,source=$volume,target=/proof,readonly" busybox:1.37.0 sh -ec '
  test "$(cat /proof/value)" = leon-docker35-persistence
  printf "PASS volume_survived_container_recreation\n"
'
docker volume rm "$volume"
printf 'PASS test_volume_cleanup\n'
docker image inspect hello-world:latest busybox:1.37.0 --format '{{.RepoTags}} {{.RepoDigests}} {{.Architecture}}'
docker ps -a --format '{{.Names}} {{.Status}}'
