#!/bin/busybox sh
set -eu
trap 's=$?; if [ "$s" -ne 0 ]; then journalctl --no-pager -o cat -n 200; fi' EXIT
/usr/libexec/platform-callpaths
mkdir -p /run/leon-rc /var/run/samba /etc/samba /tmp/share
chmod 700 /run/leon-rc
umask 077
ip link set lo up
# The actual shipped BusyBox logger and kernel logger, unchanged.
printf '/\000\000UTC\000/usr/bin:/usr/sbin:/bin:/sbin\000/sbin/syslogd\000-m\0000\000-S\000-O\000/tmp/platform-syslog\000-s\00016\000' >/run/leon-rc/syslogd.argv
printf '/\000\000UTC\000/usr/bin:/usr/sbin:/bin:/sbin\000/sbin/klogd\000-c\0005\000' >/run/leon-rc/klogd.argv
systemctl start asus-syslogd.service asus-klogd.service
/bin/busybox logger -t platform PLATFORM_LOG_BEFORE
sleep 1
grep -q PLATFORM_LOG_BEFORE /tmp/platform-syslog
p=$(/bin/busybox pidof syslogd)
kill -KILL "$p"
i=0
while test "$(/bin/busybox pidof syslogd)" = "$p" || ! systemctl is-active --quiet asus-syslogd.service; do
 i=$((i+1));test "$i" -lt 12;sleep 1
done
/bin/busybox logger -t platform PLATFORM_LOG_AFTER
sleep 1
grep -q PLATFORM_LOG_AFTER /tmp/platform-syslog
systemctl stop asus-klogd.service asus-syslogd.service
! /bin/busybox pidof syslogd
! /bin/busybox pidof klogd
echo LAB_PLATFORM_REAL_LOGGER_RESTART_PASS
# Real Samba daemons: isolated loopback guest share, no physical disks/network.
grep -q '^nobody:' /etc/passwd || printf 'nobody:x:65534:65534:nobody:/:/bin/false\n' >> /etc/passwd
grep -q '^nobody:' /etc/group || printf 'nobody:x:65534:\n' >> /etc/group
cat >/etc/smb.conf <<'EOT'
[global]
workgroup = WORKGROUP
netbios name = LEONLAB
interfaces = 127.0.0.1
bind interfaces only = yes
security = share
guest account = nobody
log file = /tmp/samba-%m.log
lock directory = /var/run/samba
pid directory = /var/run/samba
[lab]
path = /tmp/share
guest ok = yes
read only = no
EOT
printf '/\000\000UTC\000/usr/bin:/usr/sbin:/bin:/sbin\000/usr/sbin/nmbd\000-D\000-s\000/etc/smb.conf\000' >/run/leon-rc/nmbd.argv
printf '/\0001\000UTC\000/usr/bin:/usr/sbin:/bin:/sbin\000/usr/sbin/smbd\000-D\000-s\000/etc/smb.conf\000' >/run/leon-rc/smbd.argv
systemctl start asus-nmbd.service asus-smbd.service
for u in nmbd smbd; do
 systemctl is-active --quiet asus-$u.service
 for p in $(/bin/busybox pidof $u); do grep -q "/asus-$u.service$" /proc/$p/cgroup; done
done
p=$(/bin/busybox pidof smbd)
grep -q 'Cpus_allowed_list:.*1$' /proc/$p/status
/usr/libexec/smb-negotiate-probe
systemctl stop asus-smbd.service asus-nmbd.service
! /bin/busybox pidof smbd
! /bin/busybox pidof nmbd
echo LAB_PLATFORM_REAL_SAMBA_AFFINITY_PROTOCOL_PASS
