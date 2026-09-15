#!/usr/bin/bash
set -eu
docker=/usr/local/bin/docker
network=leon-armel-multiarch-test
server=leon-armel-multiarch-http
case "${1:-all}" in all|--custom-only) ;; *) exit 89;; esac
test -z "$("$docker" ps -aq --filter name="^/$server\$")"
if "$docker" network inspect "$network" >/dev/null 2>&1; then
    echo 'Test network already exists; refusing to reuse it' >&2
    exit 90
fi
"$docker" image inspect alpine:3.23 --format '{{.Id}} {{json .RepoDigests}}'
if [ "${1:-all}" != --custom-only ]; then
"$docker" run --rm --pull=never --memory=128m --memory-swap=192m --pids-limit=64 \
    --label leon.test=armel-multiarch alpine:3.23 sh -ec '
    ip -4 addr show eth0
    ip -4 route
    nslookup example.com
    wget -T 20 -qO /tmp/example http://example.com
    test -s /tmp/example
    apk add --no-cache curl ca-certificates
    curl --fail --max-time 30 --silent --show-error -o /tmp/example-https \
      -w "HTTPS status=%{http_code} verify=%{ssl_verify_result}\n" https://example.com
    test -s /tmp/example-https
    echo DEFAULT_BRIDGE_DNS_HTTP_HTTPS_PASS
    '
fi
"$docker" run --rm --pull=never --network none --memory=32m --memory-swap=32m --pids-limit=32 \
    busybox:1.37.0 busybox --list | grep -x httpd >/dev/null
network_id=$($docker network create --label leon.test=armel-multiarch "$network")
http_id=
cleanup_failed() {
    if [ -n "$http_id" ]; then
        "$docker" logs "$http_id"
        "$docker" rm -f "$http_id" >/dev/null
    fi
    "$docker" network rm "$network_id" >/dev/null
}
trap cleanup_failed EXIT
http_id=$($docker run -d --pull=never --name "$server" --network "$network" \
    --label leon.test=armel-multiarch --memory=32m --memory-swap=32m --pids-limit=32 \
    -p 192.168.100.10:18098:8080 busybox:1.37.0 sh -ec \
    'mkdir -p /www; echo GT-BE98-armel-multiarch-network-ok > /www/index.html; exec busybox httpd -f -p 8080 -h /www')
test "$($docker inspect "$server" --format '{{.State.Running}}')" = true
"$docker" run --rm --pull=never --network "$network" --memory=32m --memory-swap=32m --pids-limit=32 \
    --label leon.test=armel-multiarch alpine:3.23 sh -ec '
    nslookup leon-armel-multiarch-http
    wget -T 20 -qO- http://leon-armel-multiarch-http:8080/
    nslookup example.com
    wget -T 20 -qO /tmp/example http://example.com
    test -s /tmp/example
    echo CUSTOM_NETWORK_DNS_HTTP_PASS
    '
"$docker" inspect "$server" --format 'PID={{.State.Pid}} memory={{.HostConfig.Memory}} swap={{.HostConfig.MemorySwap}} pids={{.HostConfig.PidsLimit}} ports={{json .NetworkSettings.Ports}}'
echo LAN_PORT_READY
trap - EXIT
# The host checks port 18098, then removes this labelled test server/network.
