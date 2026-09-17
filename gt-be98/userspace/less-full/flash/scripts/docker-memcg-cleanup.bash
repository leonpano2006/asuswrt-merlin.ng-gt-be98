#!/usr/bin/bash
set -euo pipefail
docker=/usr/local/bin/docker
server=leon-rmerlin-upstream-http
network=leon-rmerlin-upstream-test
test "$("$docker" inspect "$server" --format '{{index .Config.Labels "leon.test"}}')" = rmerlin-upstream
test "$("$docker" network inspect "$network" --format '{{index .Labels "leon.test"}}')" = rmerlin-upstream
pid=$("$docker" inspect "$server" --format '{{.State.Pid}}')
memory_path=$(awk -F: '$2=="memory" {print $3}' "/proc/$pid/cgroup")
test -n "$memory_path"
base="/sys/fs/cgroup/memory$memory_path"
memory_limit=$(cat "$base/memory.limit_in_bytes")
memory_swap_limit=$(cat "$base/memory.memsw.limit_in_bytes")
failcnt=$(cat "$base/memory.failcnt")
printf 'memory_limit=%s\nmemory_plus_swap_limit=%s\nfailcnt=%s\n' "$memory_limit" "$memory_swap_limit" "$failcnt"
test "$memory_limit" = 33554432
test "$memory_swap_limit" = 33554432
test "$failcnt" = 0
"$docker" rm -f "$server"
"$docker" network rm "$network"
test -z "$("$docker" ps -aq --filter label=leon.test=rmerlin-upstream)"
test -z "$("$docker" network ls -q --filter label=leon.test=rmerlin-upstream)"
echo RMERLIN_MEMCG_AND_TEST_CLEANUP_PASS
