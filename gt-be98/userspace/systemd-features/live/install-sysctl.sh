#!/bin/sh
set -eu
payload=/tmp/leon-procps-sysctl-20260917
expected=3127dca99e1134d096d1f67a8086b54267d6c252270a55f583007f46b74d711f
test "$(sha256sum "$payload" | cut -d ' ' -f1)" = "$expected"
chmod 755 "$payload"
"$payload" --version
test "$("$payload" -n kernel.osrelease)" = "$(cat /proc/sys/kernel/osrelease)"
test "$("$payload" -n net.ipv4.ip_forward)" = "$(cat /proc/sys/net/ipv4/ip_forward)"
"$payload" --help > /tmp/leon-sysctl-help-20260917
for option in --load --system --pattern --dry-run; do grep -q -- "$option" /tmp/leon-sysctl-help-20260917; done
awk '$2=="/usr/local" && $3=="btrfs"{ok=1}END{exit !ok}' /proc/mounts
dest=/usr/local/sbin/sysctl
test ! -e "$dest" && test ! -L "$dest"
staged=$(mktemp /usr/local/sbin/.leon-sysctl-XXXXXX)
trap 'rm -f "$staged"' EXIT
cp "$payload" "$staged"
chmod 755 "$staged"
chown 0:0 "$staged"
test "$(sha256sum "$staged" | cut -d ' ' -f1)" = "$expected"
mv "$staged" "$dest"
trap - EXIT
/usr/bin/bash -lic 'hash -r; type sysctl; sysctl --version; sysctl kernel.osrelease'
echo PROCPS_SYSCTL_INSTALLED_NO_PARAMETERS_CHANGED
