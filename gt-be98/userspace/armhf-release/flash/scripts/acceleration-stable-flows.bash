#!/usr/bin/bash
set -eu
# Flow-table totals are not monotonic: old flows expire between observations.
# Retain only a flow identifier and hardware counters locally; export aggregates.
work=$(mktemp -d /tmp/leon-hwa-XXXXXX)
trap 'rm -r "$work"' EXIT
sample() {
  awk '
    /^Flow .*HW_TotalBytes/ {header=1; next}
    header && $1 ~ /^[0-9]+$/ {
      k=0
      for(i=2;i<=NF;i++) if($i ~ /^0x[0-9a-fA-F]+$/){k=i;break}
      if(!k || $(k+3) !~ /^[0-9]+$/ || $(k+4) !~ /^[0-9]+$/) exit 2
      printf "%s:%s %.0f %.0f\n",$1,$k,$(k+3),$(k+4)
    }
    END {if(!header)exit 2}
  ' /proc/fcache/l2list
}
sample > "$work/before"
sleep 20
sample > "$work/after"
awk '
  NR==FNR {hits[$1]=$2;bytes[$1]=$3;next}
  $1 in hits && $2>=hits[$1] && $3>=bytes[$1] {
    retained++
    if($2>hits[$1] && $3>bytes[$1]) {advancing++;dh+=$2-hits[$1];db+=$3-bytes[$1]}
  }
  END {
    printf "retained_flows=%d advancing_flows=%d HW_hits_delta=%.0f HW_bytes_delta=%.0f\n",retained,advancing,dh,db
    if(!advancing || dh<=0 || db<=0)exit 1
  }
' "$work/before" "$work/after"
/bin/fc status | grep 'HW Acceleration <Enabled>'
echo SYSTEMD_HARDWARE_FLOW_PROGRESS_PASS
