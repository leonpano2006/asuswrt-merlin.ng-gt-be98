#!/usr/bin/bash
set -euo pipefail
printf 'available_eraseblocks %s\n' "$(cat /sys/class/ubi/ubi0/avail_eraseblocks)"
printf 'eraseblock_size %s\n' "$(cat /sys/class/ubi/ubi0/eraseblock_size)"
for d in /sys/class/ubi/ubi0_*; do
  printf 'volume %s %s %s\n' "${d##*/}" "$(cat "$d/name")" "$(cat "$d/reserved_ebs")"
done
