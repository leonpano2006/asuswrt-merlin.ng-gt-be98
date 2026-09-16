#!/bin/sh
set -eu
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
attempt=0
while [ "$attempt" -lt 120 ]; do
    if awk '$2=="/usr/local" && $3=="btrfs"{ok=1}END{exit !ok}' /proc/mounts &&
       [ -x /usr/local/bin/dockerd ] && [ -x /jffs/scripts/local-mount ]; then
        : > /run/leon-local-ready
        echo LEON_USB_LOCAL_READY
        exit 0
    fi
    attempt=$((attempt + 1))
    sleep 1
done
echo 'Existing USB /usr/local mount did not become ready' >&2
exit 1
