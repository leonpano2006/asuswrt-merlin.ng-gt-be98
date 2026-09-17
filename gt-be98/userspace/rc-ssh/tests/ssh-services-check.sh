#!/bin/busybox sh
set -eu
trap 'status=$?; if test "$status" -ne 0; then journalctl --no-pager -o cat -u asus-rc.service -u asus-sshd.service; cat /run/ssh-auth-error 2>/dev/null || :; fi' EXIT
mkdir -p /run/systemd/system/asus-rc.service.d /root /jffs
mount -t tmpfs jffs-simulation /jffs
cat > /run/systemd/system/asus-rc.service.d/90-ssh-lab.conf <<'EOF'
[Unit]
FailureAction=none
[Service]
ExecStart=
ExecStart=/usr/libexec/leon-rc-broker --test-power /usr/libexec/ssh-services-probe
EOF
# Test-only account/key material lives in the offline VM's RAM filesystem.
# This replaces the ordinary ASUS account setup omitted by the hardware stub.
printf 'root:x:0:0:QEMU SSH test:/root:/bin/sh\n' > /etc/passwd
printf 'root:x:0:\n' > /etc/group
printf 'root:$6$lab$not-a-valid-password-hash:19000:0:99999:7:::\n' > /etc/shadow
chmod 600 /etc/shadow
printf '/bin/sh\n/bin/bash\n' > /etc/shells
chmod 700 /root
dropbearkey -t ed25519 -f /run/ssh-test-key > /run/ssh-key-output
sed -n '/^ssh-ed25519 /p' /run/ssh-key-output > /run/ssh-test.pub
test -s /run/ssh-test.pub
ip link set lo up
systemctl daemon-reload
systemctl start asus-rc.service
systemctl is-active --quiet asus-sshd.service
systemctl stop asus-rc.service
/usr/libexec/check-ssh-stopped
journalctl --sync
journalctl --no-pager -o cat -u asus-rc.service > /run/ssh-services-journal
for name in LEGACY_POLICY_CHILD_ROUTING PRE_READY_AUTH_KEYS_IDEMPOTENT RECONFIGURE_RECOVERY_ISOLATION DUPLICATE_ARGUMENT_GUARDS FAILURE_NO_FALLBACK READY DRAIN; do
    grep -qx "LAB_SSH_${name}_PASS" /run/ssh-services-journal
    echo "LAB_SSH_${name}_PASS"
done
echo LAB_SSH_PARTOF_SESSION_STOP_PASS
rm /run/systemd/system/asus-rc.service.d/90-ssh-lab.conf
rmdir /run/systemd/system/asus-rc.service.d
systemctl daemon-reload
systemctl reset-failed
echo LAB_SSH_ALL_PASS
