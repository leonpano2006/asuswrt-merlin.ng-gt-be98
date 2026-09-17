#!/bin/busybox sh
set -eu
trap 's=$?; if [ "$s" -ne 0 ]; then journalctl --no-pager -o cat -n 240; fi' EXIT
mkdir -p /run/systemd/system/asus-rc.service.d
cat > /run/systemd/system/asus-rc.service.d/90-platform-lab.conf <<'EOT'
[Unit]
FailureAction=none
[Service]
ExecStart=
ExecStart=/usr/libexec/leon-rc-broker --test-power /usr/libexec/platform-services-probe
EOT
# These fixtures test lifecycle behavior, not wireless hardware. Production
# files remain unchanged in the image; bind mounts exist only in this VM.
for d in /usr/sbin /usr/bin; do
 mkdir -p /run/fixture$d
 cp -a "$d/." /run/fixture$d/
 mount --bind /run/fixture$d "$d"
done
while read name binary comm; do
 rm -f "$binary"
 cp /usr/libexec/daemon-fixture "$binary"
done < /usr/libexec/platform-daemon-list
systemctl daemon-reload
systemctl start asus-rc.service
systemctl stop asus-rc.service
for u in $(cat /usr/libexec/platform-unit-list); do
 i=0
 until test "$(systemctl show asus-$u.service -p ActiveState --value)" = inactive; do
  i=$((i+1));test "$i" -lt 12;sleep 1
 done
 p=$(cat /run/fixture-$u);test ! -d /proc/$p
done
journalctl --sync
journalctl --no-pager -o cat -u asus-rc.service >/run/platform-journal
for marker in MANAGER_AUTH 23_PRE_READY_START SUPERVISOR_RECOVERY PRIMARY_EXIT_WITH_WORKER STOP_GROUP_ISOLATION EXTERNAL_DUPLICATE BAD_CONFIG_NO_FALLBACK READY DRAIN; do
 grep -qx "LAB_PLATFORM_${marker}_PASS" /run/platform-journal
 echo "LAB_PLATFORM_${marker}_PASS"
done
echo LAB_PLATFORM_PARTOF_STOP_PASS
