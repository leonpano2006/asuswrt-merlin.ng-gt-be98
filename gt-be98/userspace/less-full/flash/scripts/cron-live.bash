#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/bin:/usr/sbin:/bin:/sbin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
job=leon_systemd257_live_test
work=/run/leon-systemd257-cron-test
test ! -e "$work"
if cru l | grep -Fq "#$job#"; then exit 1; fi
mkdir -m 700 "$work"
registered=no
cleanup() {
    if [ "$registered" = yes ]; then cru d "$job"; fi
    rm -f "$work/job" "$work/ran" "$work/cgroup"
    rmdir "$work"
}
trap cleanup EXIT
cat > "$work/job" <<'EOF'
#!/usr/bin/bash
umask 077
cat /proc/self/cgroup > /run/leon-systemd257-cron-test/cgroup
date -u > /run/leon-systemd257-cron-test/ran
EOF
chmod 700 "$work/job"
before=$(systemctl show asus-crond.service -p MainPID --value)
test "$before" -gt 1
/sbin/service restart_crond
for i in $(seq 1 20); do
    after=$(systemctl show asus-crond.service -p MainPID --value)
    if [ "$after" -gt 1 ] && [ "$after" != "$before" ]; then break; fi
    sleep 1
done
test "$after" -gt 1
test "$after" != "$before"
test "$(pidof crond)" = "$after"
cru a "$job" "* * * * * $work/job"
registered=yes
for i in $(seq 1 75); do
    [ ! -s "$work/ran" ] || break
    sleep 1
done
test -s "$work/ran"
grep -q '/asus-crond.service' "$work/cgroup"
printf 'CRON_BEFORE=%s\nCRON_AFTER=%s\n' "$before" "$after"
cat "$work/ran" "$work/cgroup"
test "$(systemctl is-active asus-crond.service)" = active
test "$(systemctl is-active asus-rc.service)" = active
echo SYSTEMD_CRON_REAL_SCHEDULE_AND_RC_RESTART_PASS
