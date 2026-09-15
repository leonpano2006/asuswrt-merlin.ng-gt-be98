#!/usr/bin/bash
set -eu
date -u '+%Y-%m-%d %H:%M:%S UTC'
uname -a
cat /proc/uptime
for p in /proc/sys/net/ipv4/ip_forward /proc/sys/net/ipv6/conf/all/forwarding /proc/sys/net/ipv6/conf/default/forwarding /proc/sys/net/bridge/bridge-nf-call-iptables /proc/sys/net/bridge/bridge-nf-call-ip6tables /proc/sys/net/bridge/bridge-nf-call-arptables; do
  if [ -f "$p" ]; then printf 'SYSCTL %s=' "$p"; cat "$p"; fi
done
for name in iptables-save ip6tables-save; do
  if command -v "$name" >/dev/null; then
    printf 'RULESET_SHA256 %s ' "$name"
    "$name" | sed -E '/^#/d; s/\[[0-9]+:[0-9]+\]/[COUNTERS]/g' | sha256sum
  else printf 'RULESET_UNAVAILABLE %s\n' "$name"; fi
done
for p in /sys/class/net/*; do
  printf 'INTERFACE %s master=%s\n' "${p##*/}" "$(readlink "$p/master" || true)"
done
printf 'FC_STATUS\n'
/bin/fc status
printf 'PKTRUNNER_STATS\n'
cat /proc/pktrunner/accel0/stats
printf 'CGROUPS\n'
cat /proc/cgroups
