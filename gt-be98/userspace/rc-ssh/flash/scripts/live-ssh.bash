#!/usr/bin/bash
set -euo pipefail
export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
test "$(systemctl is-active asus-sshd.service)" = active
test "$(systemctl show asus-sshd.service -p Result --value)" = success
test "$(systemctl show asus-sshd.service -p NRestarts --value)" = 0
main=$(systemctl show asus-sshd.service -p MainPID --value)
test "$main" -gt 1
test "$(readlink /proc/$main/exe)" = /usr/bin/dropbearmulti
grep -q '/asus-sshd.service$' /proc/$main/cgroup
tr '\000' '\n' < /proc/$main/cmdline > /run/leon8-ssh-argv
grep -qx /usr/sbin/dropbear /run/leon8-ssh-argv
grep -qx -- -F /run/leon8-ssh-argv
grep -qx -- "$(nvram get sshd_port)" /run/leon8-ssh-argv
for pid in $(pidof dropbear); do
    grep -q '/asus-sshd.service$' /proc/$pid/cgroup
done
test "$(stat -c '%u:%a' /run/leon-rc/sshd.argv)" = 0:600
test "$(stat -c '%u:%a' /run/leon-rc)" = 0:700
test "$(systemctl show asus-sshd.service -p KillMode --value)" = control-group
test "$(systemctl show asus-sshd.service -p Restart --value)" = always
systemctl show asus-sshd.service -p ActiveState -p SubState -p MainPID -p Result -p NRestarts -p ControlGroup -p PartOf
printf 'SSH_MAIN_PID=%s\n' "$main"
sha256sum /jffs/.ssh/* /root/.ssh/authorized_keys
echo LIVE_SSH_FOREGROUND_OWNERSHIP_AND_POLICY_PASS
