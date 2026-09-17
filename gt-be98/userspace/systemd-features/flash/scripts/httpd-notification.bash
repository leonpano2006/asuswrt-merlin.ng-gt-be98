#!/usr/bin/bash
set -eu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
test "$(readlink /proc/1/exe)" = /usr/lib/systemd/systemd
test "$(systemctl is-active asus-rc.service)" = active
before=$(pidof httpd)
test -n "$before"
set -- $before
expected_count=$#
broker=$(systemctl show asus-rc.service -p MainPID --value)
/sbin/service restart_httpd
for i in $(seq 1 40); do
    after=$(pidof httpd || true)
    set -- $after
    fresh=1
    for old in $before; do
        case " $after " in *" $old "*) fresh=0;; esac
    done
    if [ "$#" = "$expected_count" ] && [ "$fresh" = 1 ]; then break; fi
    sleep 1
done
test -n "$after"
test "$fresh" = 1
set -- $after
test "$#" = "$expected_count"
test "$(systemctl show asus-rc.service -p MainPID --value)" = "$broker"
test "$(systemctl is-active asus-rc.service)" = active
leon-rcctl ping
printf 'HTTPD_BEFORE=%s\nHTTPD_AFTER=%s\nBROKER_PID=%s\n' "$before" "$after" "$broker"
echo SYSTEMD_REAL_HTTPD_NOTIFICATION_PASS
