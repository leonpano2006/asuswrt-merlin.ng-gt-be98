#!/usr/bin/env python3
"""Boot the production init in offline QEMU, substituting only the ASUS backend."""
from pathlib import Path
import argparse
import gzip
import json
import shutil
import stat
import subprocess
from common import inventory, sha

r=Path(__file__).resolve().parents[1]; w=r.parent
p=argparse.ArgumentParser();p.add_argument('--revision',required=True);a=p.parse_args()
assert a.revision.replace('-','').isalnum()
out=r/'build'/a.revision;out.mkdir(exist_ok=False)
root=out/'rootfs';base=r/'build/production-rootfs'
subprocess.run(['cp','-a','--reflink=auto',str(base),str(root)],check=True)
old=w/'systemd-lab-20260916/build/guard-service/rootfs'
units=root/'usr/lib/systemd/system'
for name in ('leon-check.service','leon-worker.service','leon-guard.service'):
    shutil.copy2(old/'usr/lib/systemd/system'/name,units/name)
# The added real haveged runs each spend about 15 s collecting jitter under
# TCG. Bound the complete lab suite separately from production unit timeouts.
checkunit=units/'leon-check.service'
checktext=checkunit.read_text()
import re
assert re.search(r'^TimeoutStartSec=.*$',checktext,re.M)
checkunit.write_text(re.sub(r'^TimeoutStartSec=.*$','TimeoutStartSec=160',checktext,flags=re.M))
(units/'leon-boot-test.target').write_text('[Unit]\nDescription=Production early boot rehearsal\nDefaultDependencies=no\nRequires=leon-check.service\nAfter=leon-check.service\n')
for name in ('leon-systemd-guardcheck',):shutil.copy2(old/'usr/libexec'/name,root/'usr/libexec'/name)
shutil.copytree(old/'usr/lib/arm-linux-gnueabi/leon-systemd-lab',root/'usr/lib/arm-linux-gnueabi/leon-systemd-lab')
for path in (r/'build/probes').iterdir():shutil.copy2(path,root/'usr/libexec'/path.name)
text=(units/'asus-rc.service').read_text().replace('FailureAction=reboot\n','')
(units/'asus-rc-lab.service').write_text(text.replace('/usr/libexec/leon-rc-broker /usr/sbin/rc',
    '/usr/libexec/leon-rc-broker --test-power /usr/libexec/rc-probe'))
(units/'asus-rc-real-power.service').write_text(text.replace('/usr/libexec/leon-rc-broker /usr/sbin/rc',
    '/usr/libexec/leon-rc-broker /usr/libexec/rc-probe'))
shutil.copy2(r/'tests/compat-check.sh',root/'usr/libexec/leon-rc-compat-check')
(root/'usr/libexec/leon-rc-compat-check').chmod(0o755)
check=(w/'systemd-lab-20260916/scripts/lab-check.sh').read_text()
check=check.replace('echo LAB_SYSTEMD_ALL_PASS', '/rom/etc/init.d/mount-fs.sh stop\n'
    'awk \'$2=="/var" && $3=="tmpfs"{ok=1}END{exit !ok}\' /proc/mounts\n'
    'awk \'$2=="/tmp/mnt" && $3=="tmpfs"{ok=1}END{exit !ok}\' /proc/mounts\n'
    'test -S /run/systemd/private\necho LAB_BSP_PRESERVES_SYSTEMD_MOUNTS_PASS\n'
    '/usr/libexec/leon-rc-compat-check\necho LAB_REAL_EARLY_INIT_PASS\necho LAB_SYSTEMD_ALL_PASS')
check=check.replace('systemctl --no-block poweroff','leon-rcctl poweroff')
(root/'usr/libexec/leon-systemd-lab-check').write_text(check)
(root/'usr/libexec/leon-systemd-lab-check').chmod(0o755)
before=inventory(base);after=inventory(root)
changed=[name for name in before if before[name]!=after[name]]
assert not changed,changed
assert not before.keys()-after.keys()
(out/'production-preservation.json').write_text(json.dumps({'all_production_paths_identical':True,
    'production_init_sha256':sha(root/'usr/sbin/init'),'added_test_paths':sorted(after.keys()-before.keys())},indent=2)+'\n')
squash=out/'rootfs.squashfs'
sort=out/'sort.txt'
subprocess.run(['python3',str(r/'scripts/make-squashfs-sort.py'),str(root),str(sort)],check=True)
with (out/'squashfs.log').open('w') as log:
    subprocess.run(['mksquashfs',str(root),str(squash),'-noappend','-all-root','-comp','zstd','-Xcompression-level','22',
        '-b','1048576','-tailends','-sort',str(sort),'-processors','4','-mem','512M','-no-progress','-exit-on-error','-mkfs-time','1789560000'],stdout=log,stderr=subprocess.STDOUT,check=True)
raw=gzip.decompress((w/'systemd-lab-20260916/build/guard-service/guest.cpio.gz').read_bytes());pos=0
busybox=None
while pos<len(raw):
    assert raw[pos:pos+6]==b'070701'
    fields=[int(raw[pos+6+8*i:pos+14+8*i],16) for i in range(13)]
    size,namesize=fields[6],fields[11];name=raw[pos+110:pos+110+namesize-1].decode();start=(pos+110+namesize+3)&~3
    if name=='bin/busybox':busybox=raw[start:start+size];break
    pos=(start+size+3)&~3
assert busybox
entries={n:(stat.S_IFDIR|0o755,b'',0,0) for n in ('bin','dev','proc','sys','tmp','newroot')}
entries.update({'bin/busybox':(stat.S_IFREG|0o755,busybox,0,0),
    'init':(stat.S_IFREG|0o755,(r/'scripts/rehearsal-init.sh').read_bytes(),0,0),
    'rootfs.squashfs':(stat.S_IFREG|0o444,squash.read_bytes(),0,0),
    'dev/console':(stat.S_IFCHR|0o600,b'',5,1),'dev/null':(stat.S_IFCHR|0o666,b'',1,3),
    'dev/loop0':(stat.S_IFBLK|0o600,b'',7,0),'TRAILER!!!':(0,b'',0,0)})
data=bytearray()
for ino,(name,(mode,content,major,minor)) in enumerate(entries.items(),1):
    name=name.encode()+b'\0';fields=[ino,mode,0,0,2 if stat.S_ISDIR(mode) else 1,0,len(content),0,0,major,minor,len(name),0]
    data+=b'070701'+''.join(f'{x:08x}' for x in fields).encode()+name;data+=b'\0'*(-len(data)%4)
    data+=content;data+=b'\0'*(-len(data)%4)
guest=out/'guest.cpio.gz';guest.write_bytes(gzip.compress(data,compresslevel=1,mtime=0))
print(json.dumps({'rootfs_bytes':squash.stat().st_size,'guest_sha256':sha(guest),'production_paths_unchanged':True}))
