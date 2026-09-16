#!/bin/busybox sh
set -eu
# A fresh firmware boot routes the only legacy start entry into this unit.
# Refuse a second owner if somebody manually launched the old daemon.
if /bin/busybox pidof haveged >/dev/null 2>&1; then
    echo 'haveged already exists outside this service; refusing a duplicate.' >&2
    exit 1
fi
