#!/bin/bash
set -euo pipefail
bb=/tmp/leon-busybox-aarch64-20260923/busybox-aarch64
old=/usr/bin/busybox
expected=2931fe7011b56e4de43bb53ae87377037bfe3779295c5baa2ca3fe4b04915f28
before=$(sha256sum "$old")
actual=$(sha256sum "$bb")
[[ ${actual%% *} == "$expected" ]]
printf 'Candidate SHA256: %s\n' "${actual%% *}"
/opt/bin/file "$bb"
/lib/ld-linux-aarch64.so.1 --list "$bb"
work=$(mktemp -d /tmp/bb64-check.XXXXXX)
trap 'rm -rf "$work"' EXIT
"$old" --list > "$work/old-applets"
"$bb" --list > "$work/new-applets"
cmp "$work/old-applets" "$work/new-applets"
printf 'Identical applets: '
wc -l < "$work/new-applets"
"$bb" sh -c 'test "$((2147483648 + 1))" = 2147483649'
[[ $("$bb" date -u -d @2147483648 +%Y-%m-%dT%H:%M:%SZ) == 2038-01-19T03:14:08Z ]]
"$old" sh -c 'exec /tmp/leon-busybox-aarch64-20260923/busybox-aarch64 true'
"$bb" sh -c 'exec /usr/bin/busybox true'
printf 'Shell, post-2038 date and cross-architecture exec: PASS\n'
printf 'alpha\n' > "$work/input"
[[ $("$bb" sed s/alpha/beta/ "$work/input") == beta ]]
[[ $("$bb" awk 'BEGIN { print 3*7 }') == 21 ]]
"$bb" cp "$work/input" "$work/copy"
cmp "$work/input" "$work/copy"
"$bb" tar -cf "$work/test.tar" -C "$work" input
[[ $("$bb" tar -tf "$work/test.tar") == input ]]
"$bb" ps > "$work/processes"
"$bb" mount > "$work/mounts"
"$bb" df -k /tmp
printf 'Text/file/archive/process/mount checks: PASS\n'
set +e
"$old" logread > "$work/old-log" 2> "$work/old-log.err"
old_status=$?
"$bb" logread > "$work/new-log" 2> "$work/new-log.err"
new_status=$?
set -e
printf 'Read existing syslog IPC: old_status=%s new_status=%s old_bytes=%s new_bytes=%s\n' \
    "$old_status" "$new_status" "$(wc -c < "$work/old-log")" "$(wc -c < "$work/new-log")"
[[ $old_status == "$new_status" ]]
if [ "$old_status" = 0 ]; then
    cmp -s "$work/old-log" "$work/new-log" && printf 'Syslog snapshots identical\n' || printf 'Syslog snapshots differ (live log may advance)\n'
fi
for target in 127.0.0.1 192.168.100.1 1.1.1.1 syd.lg.speedypage.com; do
    printf '\nPING %s\n' "$target"
    /usr/bin/timeout 10 "$bb" ping -c 3 -W 2 "$target"
done
set +e
SECONDS=0
/usr/bin/timeout 6 "$bb" ping -n -t 1 -w 3 1.1.1.1 > "$work/deadline" 2>&1
deadline_status=$?
elapsed=$SECONDS
set -e
printf 'Deadline status=%s elapsed_seconds=%s\n' "$deadline_status" "$elapsed"
[[ $deadline_status == 1 && $elapsed -ge 2 && $elapsed -le 4 ]]
[[ $(sha256sum "$old") == "$before" ]]
printf 'System BusyBox unchanged: %s\n' "$before"
printf 'Failed systemd units: '
systemctl --failed --no-legend --no-pager | wc -l
curl -ksS --max-time 8 -o /dev/null -w 'Management HTTP status: %{http_code}\n' https://127.0.0.1:8443/
printf 'Router candidate checks: PASS\n'
