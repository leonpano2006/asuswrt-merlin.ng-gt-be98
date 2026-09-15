#!/usr/bin/bash
# Apply only to the inspected hooks. Keep existing user/Claude customizations.
set -euo pipefail
export PATH=/usr/bin:/usr/sbin:/bin:/sbin
stage=/jffs/docker/migration-network-local-20260915
backup=/jffs/docker/backups/network-local-20260915
check() { [ "$(sha256sum "$1" | cut -d ' ' -f1)" = "$2" ]; }
check /jffs/scripts/post-mount e9bbf7df905d49d4dfc5048c4fb57176e7bff1ab16fbd4401c9b28a19bbde287
check /jffs/scripts/services-start c44b36aeb8c225b5d0b6016cae50f72793c3531465dfe9ac45bfc41cee9a879b
check /jffs/configs/profile.add 17b9bd8aed28eb43f48b808583c9db339d59a5710b4aeceb07d8a31f0f7ea92d
[ ! -e /jffs/scripts/firewall-start ] && [ ! -L /jffs/scripts/firewall-start ]
[ ! -e /jffs/scripts/nat-start ] && [ ! -L /jffs/scripts/nat-start ]
for f in post-mount services-start profile.add; do bash -n "$stage/build/$f"; done
mkdir -p /tmp/leon-local-realjffs
mount -t ubifs ubi:jffs2 /tmp/leon-local-realjffs
trap 'umount /tmp/leon-local-realjffs' EXIT
check /tmp/leon-local-realjffs/scripts/post-mount e9bbf7df905d49d4dfc5048c4fb57176e7bff1ab16fbd4401c9b28a19bbde287
cp -p /tmp/leon-local-realjffs/scripts/post-mount "$backup/underlying-post-mount"
install_file() {
    cp "$1" "$2.local-new"
    chmod "$3" "$2.local-new"
    mv "$2.local-new" "$2"
}
install_file "$stage/build/post-mount" /tmp/leon-local-realjffs/scripts/post-mount 755
install_file "$stage/build/post-mount" /jffs/scripts/post-mount 755
install_file "$stage/build/services-start" /jffs/scripts/services-start 755
install_file "$stage/build/profile.add" /jffs/configs/profile.add 644
install_file "$stage/scripts/firewall-hook.sh" /jffs/scripts/firewall-start 755
install_file "$stage/scripts/firewall-hook.sh" /jffs/scripts/nat-start 755
cmp /jffs/scripts/post-mount /tmp/leon-local-realjffs/scripts/post-mount
# Retire only the three links installed by our earlier Docker smoke test.
for pair in 'docker:/jffs/docker/bin/docker' 'docker-start:/jffs/docker/start.bash' 'docker-stop:/jffs/docker/stop.bash'; do
    name=${pair%%:*}; target=${pair#*:}
    if [ -L "/opt/bin/$name" ] && [ "$(readlink "/opt/bin/$name")" = "$target" ]; then
        cp -a "/opt/bin/$name" "$backup/opt-$name"
        rm "/opt/bin/$name"
    fi
done
/jffs/scripts/local-mount
/jffs/scripts/local-mount
sync
echo LOCAL_HOOKS_INSTALLED
