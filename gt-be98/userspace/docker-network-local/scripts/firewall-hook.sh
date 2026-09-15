#!/bin/sh
# Shared body for Merlin firewall-start and nat-start. The helper serializes
# events and does nothing when Docker is stopped. No automatic daemon startup.
if [ -x /usr/local/sbin/docker-firewall-reconcile ]; then
    nohup /usr/local/sbin/docker-firewall-reconcile --force >> /jffs/docker/logs/firewall-reconcile.log 2>&1 </dev/null &
fi
