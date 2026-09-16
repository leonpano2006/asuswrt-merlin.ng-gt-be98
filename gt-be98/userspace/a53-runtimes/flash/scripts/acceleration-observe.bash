#!/usr/bin/bash
set -eu
# Read-only observation. Export aggregate counters, never flow addresses or ports.
# Do not reset counters, flush flows, change forwarding, or toggle acceleration.
for sample in 1 2; do
  printf 'SAMPLE=%s\n' "$sample"
  date -u '+%Y-%m-%d %H:%M:%S UTC'
  cat /proc/uptime
  awk '/^cpu[ 0-9]/{print}' /proc/stat
  for table in l2list nflist; do
    awk -v table="$table" '
      /^Flow .*HW_TotalBytes/ { header=1; next }
      header && $1 ~ /^[0-9]+$/ {
        k=0
        for (i=2; i<=NF; i++) {
          if ($i ~ /^0x[0-9a-fA-F]+$/) { k=i; break }
        }
        if (!k || $(k+2) !~ /^[0-9]+$/ || $(k+3) !~ /^[0-9]+$/ || $(k+4) !~ /^[0-9]+$/) {bad++; next}
        rows++
        hits += $(k+3)
        bytes += $(k+4)
        if ($(k+3)>0 || $(k+4)>0) with_hw++
      }
      END {
        printf "TABLE=%s header=%d rows=%d parse_errors=%d flows_with_hw_counters=%d HW_TotHits=%.0f HW_TotalBytes=%.0f\n", table,header,rows,bad,with_hw,hits,bytes
        if (!header || bad) exit 2
      }
    ' "/proc/fcache/$table"
  done
  cat /proc/pktrunner/accel0/stats
  if [ "$sample" = 1 ]; then sleep 20; fi
done
printf 'FINAL_ACCELERATION_STATUS\n'
/bin/fc status
printf 'IPV4_FORWARDING='
cat /proc/sys/net/ipv4/ip_forward
