#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
before=$(systemctl show asus-sshd.service -p MainPID --value)
docker_before=$(cat /var/run/leon-docker/dockerd.pid)
test "$before" -gt 1
/sbin/service start_sshd
sleep 3
test "$(systemctl show asus-sshd.service -p MainPID --value)" = "$before"
test "$(cat /var/run/leon-docker/dockerd.pid)" = "$docker_before"
test "$(systemctl is-active leon-docker-trial.service)" = active
printf 'SSH_MAIN_PID=%s DOCKER_PID=%s\n' "$before" "$docker_before"
echo LIVE_SSH_IDEMPOTENT_START_PASS
