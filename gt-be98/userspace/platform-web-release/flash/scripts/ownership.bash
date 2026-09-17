#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
checked=0
while read -r name comm; do
    unit="asus-$name.service"
    state=$(systemctl is-active "$unit" || true)
    # ASUS pidof also matches the shared executable basename: httpds runs
    # /usr/sbin/httpd. Filter on /proc/comm to distinguish the two instances.
    pids=
    for pid in $(pidof "$comm" || true); do
        if [ "$(cat /proc/$pid/comm)" = "$comm" ]; then pids="$pids $pid"; fi
    done
    printf 'UNIT %s state=%s pids=%s\n' "$unit" "$state" "$pids"
    test "$(systemctl show "$unit" -p Result --value)" = success
    if [ -z "$pids" ]; then
        test "$state" = inactive
        continue
    fi
    test "$state" = active
    supervisor=$(systemctl show "$unit" -p MainPID --value)
    test "$supervisor" -gt 1
    test "$(readlink /proc/$supervisor/exe)" = /usr/libexec/leon-daemon-supervisor
    for pid in $pids; do
        grep -q "/$unit" "/proc/$pid/cgroup"
        printf 'OWNED %s pid=%s supervisor=%s\n' "$comm" "$pid" "$supervisor"
    done
    checked=$((checked+1))
done <<'DAEMONS'
syslogd syslogd
klogd klogd
eapd eapd
acsd acsd
acsd2 acsd2
bsd bsd
wlceventd wlceventd
roamast roamast
httpd httpd
httpds httpds
hotplug2 hotplug2
lpd lpd
u2ec u2ec
nmbd nmbd
smbd smbd
wsdd wsdd2
networkmap networkmap
notification nt_monitor
protection protect_srv
netool netool
cfg-server cfg_server
cfg-client cfg_client
DAEMONS
test "$checked" -gt 10
echo "LEON10_PLATFORM_OWNERSHIP_PASS running_services=$checked"
