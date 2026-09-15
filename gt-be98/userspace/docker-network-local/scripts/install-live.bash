#!/usr/bin/bash
# Run the staged copy on the router. Network validation precedes boot hooks.
set -euo pipefail
export PATH=/usr/bin:/usr/sbin:/bin:/sbin
stage=/jffs/docker/migration-network-local-20260915
backup=/jffs/docker/backups/network-local-20260915
prefix=/jffs/usr-local
[ "$(nvram get productid)" = GT-BE98 ]
case "$(uname -v)" in '#36 '*) ;; *) exit 90;; esac
awk '$2=="/jffs" && $3=="btrfs"{ok=1}END{exit !ok}' /proc/mounts
[ ! -e "$backup" ] && [ ! -e "$prefix" ]
[ -d /usr/local ] && [ ! -L /usr/local ]
cd /jffs/docker/bin
sha256sum -c "$stage/configs/docker-binaries.sha256"
cd "$stage"
[ -z "$(/jffs/docker/bin/docker ps -aq)" ]
mkdir -p "$backup"
chmod 700 "$backup"
cp -a /jffs/docker/config/daemon.json /jffs/docker/start.bash /jffs/docker/stop.bash "$backup/"
cp -a /jffs/scripts/post-mount /jffs/scripts/services-start /jffs/configs/profile.add "$backup/"
iptables-save > "$backup/iptables.save"
cat /proc/sys/net/ipv4/ip_forward > "$backup/ip_forward"
cat /proc/fcache/stats/fhw > "$backup/fhw.before"
cat /proc/modules > "$backup/modules.before"
ip -4 route show table all > "$backup/routes.before"
mkdir -m 755 "$prefix"
cp -a /usr/local/. "$prefix/"
mkdir -p "$prefix/bin" "$prefix/sbin" "$prefix/libexec/docker/iptables/sbin" "$prefix/lib" "$prefix/include" "$prefix/etc"
for f in containerd containerd-shim-runc-v2 ctr docker docker-init docker-proxy dockerd runc; do
    cp -p "/jffs/docker/bin/$f" "$prefix/bin/$f"
    chown 0:0 "$prefix/bin/$f"
    chmod 755 "$prefix/bin/$f"
done
cp scripts/docker-start scripts/docker-stop scripts/docker-firewall-reconcile "$prefix/sbin/"
cp build/docker-root-view "$prefix/libexec/docker/docker-root-view"
cp build/xtables-legacy-multi "$prefix/libexec/docker/iptables/sbin/xtables-legacy-multi"
chmod 755 "$prefix/libexec/docker/iptables/sbin/xtables-legacy-multi"
for f in iptables iptables-save iptables-restore ip6tables ip6tables-save ip6tables-restore; do
    ln -s xtables-legacy-multi "$prefix/libexec/docker/iptables/sbin/$f"
done
chmod 755 "$prefix/sbin/"* "$prefix/libexec/docker/docker-root-view"
# Retain compatibility for prior scripts and the rollback mount helper.
ln -s ../libexec/docker/docker-root-view "$prefix/bin/docker-root-view"
cp scripts/local-mount /jffs/scripts/local-mount
chmod 755 /jffs/scripts/local-mount
/jffs/scripts/local-mount
[ "$prefix" -ef /usr/local ]
/jffs/docker/bin/dockerd --validate --config-file="$stage/configs/daemon.json"
/jffs/docker/stop.bash
mv /jffs/docker/bin "$backup/bin"
ln -s /usr/local/bin /jffs/docker/bin
rm /jffs/docker/start.bash /jffs/docker/stop.bash
ln -s /usr/local/sbin/docker-start /jffs/docker/start.bash
ln -s /usr/local/sbin/docker-stop /jffs/docker/stop.bash
cp configs/daemon.json /jffs/docker/config/daemon.json
chmod 600 /jffs/docker/config/daemon.json
/usr/local/sbin/docker-start
