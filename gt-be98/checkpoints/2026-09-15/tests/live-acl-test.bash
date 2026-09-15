#!/usr/bin/bash
set -euo pipefail
[[ $(uname -r) == 4.19.294 && $(uname -v) == '#35 '* ]]
grep -q 'root=/dev/ubiblock0_6' /proc/cmdline
awk '$2=="/jffs" && $3=="btrfs" {ok=1} END {exit !ok}' /proc/mounts
testdir=$(mktemp -d /jffs/.leon-acl35-test-XXXXXX)
cleanup() {
    rm -f "$testdir/explicit" "$testdir/default/inherited"
    rmdir "$testdir/default" "$testdir" 2>/dev/null || true
}
trap cleanup EXIT
/usr/bin/setfacl -b -k "$testdir"
chmod 755 "$testdir"
mkdir "$testdir/default"
/usr/bin/setfacl -b -k "$testdir/default"
chmod 755 "$testdir/default"
printf 'ACL explicit access\n' > "$testdir/explicit"
chmod 600 "$testdir/explicit"
/usr/bin/setfacl -m u:12345:r-- "$testdir/explicit"
/usr/bin/getfacl -n "$testdir/explicit"
/tmp/leon-acl-access-probe 12345 "$testdir/explicit" 1 0
/tmp/leon-acl-access-probe 12346 "$testdir/explicit" 0 0
echo LIVE_PASS acl_named_user_enforced
/usr/bin/setfacl -m m::--- "$testdir/explicit"
/tmp/leon-acl-access-probe 12345 "$testdir/explicit" 0 0
/usr/bin/setfacl -m m::r-- "$testdir/explicit"
echo LIVE_PASS acl_mask_enforced
/usr/bin/setfacl -d -m u::rwx,u:12345:r-x,g::---,m::r-x,o::--- "$testdir/default"
printf 'ACL inherited access\n' > "$testdir/default/inherited"
/usr/bin/getfacl -n "$testdir/default/inherited"
/tmp/leon-acl-access-probe 12345 "$testdir/default/inherited" 1 0
/tmp/leon-acl-access-probe 12346 "$testdir/default/inherited" 0 0
echo LIVE_PASS acl_default_inheritance
cleanup
trap - EXIT
echo LIVE_PASS acl_test_cleanup_complete
