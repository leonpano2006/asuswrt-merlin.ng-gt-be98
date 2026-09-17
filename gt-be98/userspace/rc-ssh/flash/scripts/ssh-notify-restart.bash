#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
test "$(systemctl is-active asus-sshd.service)" = active
test "$(systemctl is-active leon-docker-trial.service)" = active
printf 'SSH_MAIN_PID=%s\n' "$(systemctl show asus-sshd.service -p MainPID --value)"
printf 'DOCKER_PID=%s\n' "$(cat /var/run/leon-docker/dockerd.pid)"
/usr/local/bin/docker inspect leon-rmerlin-upstream-http --format 'CONTAINER_PID={{.State.Pid}} CONTAINER_ID={{.Id}}'
echo LIVE_SSH_NOTIFY_RESTART_REQUEST
/sbin/service restart_sshd
