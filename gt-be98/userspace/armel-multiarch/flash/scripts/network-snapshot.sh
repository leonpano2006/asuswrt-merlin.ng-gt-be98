#!/bin/sh
set -eu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
date -u
uname -a
cat /proc/uptime
for name in /proc/sys/net/ipv4/ip_forward /proc/sys/net/ipv6/conf/all/forwarding /proc/sys/net/ipv6/conf/default/forwarding; do
    printf 'SYSCTL %s=%s\n' "$name" "$(cat "$name")"
done
for tool in iptables-save ip6tables-save; do
    printf 'RULESET_SHA256 %s ' "$tool"
    "$tool" | sed '/^#/d;s/\[[0-9][0-9]*:[0-9][0-9]*\]/[0:0]/g' | sha256sum
done
for path in /sys/class/net/*; do
    test -d "$path" || continue
    printf 'INTERFACE %s master=%s\n' "${path##*/}" "$(readlink "$path/master" || true)"
done
printf 'VPN_SERVER1_STATE=%s\n' "$(nvram get vpn_server1_state)"
printf 'VPN_SERVER1_ERRNO=%s\n' "$(nvram get vpn_server1_errno)"
printf 'MODULE_NAMES\n'
awk '{print $1}' /proc/modules | sort
