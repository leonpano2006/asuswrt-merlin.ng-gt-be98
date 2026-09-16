#!/usr/bin/env python3
"""Stage an offline test rootfs. The real RC is only checked by the dynamic loader."""
from pathlib import Path
import argparse,gzip,hashlib,json,shutil,stat,subprocess
r=Path(__file__).resolve().parents[1];w=r.parent
args=argparse.ArgumentParser();args.add_argument('--revision',required=True);args.add_argument('--level',type=int,default=22);args=args.parse_args()
assert args.revision.replace('-','').isalnum() and 1<=args.level<=22
out=r/'build'/args.revision;out.mkdir(exist_ok=False)
root=out/'rootfs';base=w/'systemd-lab-20260916/build/guard-service/rootfs'
subprocess.run(['cp','-a','--reflink=auto',str(base),str(root)],check=True)
assert (r/'overlay/usr/sbin/rc').is_file()
# The stock executable is mode 0500; replace only the isolated copy.
(root/'usr/sbin/rc').unlink()
shutil.copytree(r/'overlay',root,dirs_exist_ok=True,symlinks=True)
for p in base.rglob('*'):
    if p.is_dir() and not p.is_symlink():shutil.copystat(p,root/p.relative_to(base),follow_symlinks=False)
for p in (r/'build/probes').iterdir():shutil.copy2(p,root/'usr/libexec'/p.name)
(root/'rom/etc/ld.so.preload').write_text('/usr/$LIB/libleon-rc-notify.so\n')
unit=(r/'units/asus-rc.service').read_text().replace('/usr/libexec/leon-rc-broker /usr/sbin/rc',
    '/usr/libexec/leon-rc-broker --test-power /usr/libexec/rc-probe')
(root/'usr/lib/systemd/system/asus-rc-lab.service').write_text(unit)
power=(r/'units/asus-rc.service').read_text().replace('/usr/libexec/leon-rc-broker /usr/sbin/rc',
    '/usr/libexec/leon-rc-broker /usr/libexec/rc-probe').replace('StandardOutput=journal','StandardOutput=tty\nTTYPath=/dev/console').replace('StandardError=journal','StandardError=tty')
(root/'usr/lib/systemd/system/asus-rc-real-power.service').write_text(power)
shutil.copy2(r/'tests/compat-check.sh',root/'usr/libexec/leon-rc-compat-check')
(root/'usr/libexec/leon-rc-compat-check').chmod(0o755)
check=root/'usr/libexec/leon-systemd-lab-check'
text=check.read_text().replace('echo LAB_SYSTEMD_ALL_PASS','/usr/libexec/leon-rc-compat-check\necho LAB_SYSTEMD_ALL_PASS')
text=text.replace('systemctl --no-block poweroff','leon-rcctl poweroff')
check.write_text(text)
squash=out/'rootfs.squashfs'
with (out/'squashfs.log').open('w') as log:subprocess.run(['mksquashfs',str(root),str(squash),'-noappend','-all-root',
    '-comp','zstd','-Xcompression-level',str(args.level),'-b','1048576','-tailends','-processors','4','-mem','512M',
    '-no-progress','-exit-on-error','-mkfs-time','1789560000'],stdout=log,stderr=subprocess.STDOUT,check=True)
old=w/'systemd-lab-20260916/build/guard-service/guest.cpio.gz'
raw=gzip.decompress(old.read_bytes());pos=0;busybox=None
while pos<len(raw):
    assert raw[pos:pos+6]==b'070701'
    fields=[int(raw[pos+6+8*i:pos+14+8*i],16) for i in range(13)]
    size,namesize=fields[6],fields[11];name=raw[pos+110:pos+110+namesize-1].decode();start=(pos+110+namesize+3)&~3
    if name=='bin/busybox':busybox=raw[start:start+size];break
    pos=(start+size+3)&~3
assert busybox
entries={n:(stat.S_IFDIR|0o755,b'',0,0) for n in ('bin','dev','proc','sys','tmp','newroot')}
entries.update({'bin/busybox':(stat.S_IFREG|0o755,busybox,0,0),
    'init':(stat.S_IFREG|0o755,(w/'systemd-lab-20260916/scripts/guest-init.sh').read_bytes(),0,0),
    'rootfs.squashfs':(stat.S_IFREG|0o444,squash.read_bytes(),0,0),
    'dev/console':(stat.S_IFCHR|0o600,b'',5,1),'dev/null':(stat.S_IFCHR|0o666,b'',1,3),
    'dev/loop0':(stat.S_IFBLK|0o600,b'',7,0),'TRAILER!!!':(0,b'',0,0)})
data=bytearray()
for ino,(name,(mode,content,major,minor)) in enumerate(entries.items(),1):
    name=name.encode()+b'\0';fields=[ino,mode,0,0,2 if stat.S_ISDIR(mode) else 1,0,len(content),0,0,major,minor,len(name),0]
    data+=b'070701'+''.join(f'{x:08x}' for x in fields).encode()+name;data+=b'\0'*(-len(data)%4)
    data+=content;data+=b'\0'*(-len(data)%4)
guest=out/'guest.cpio.gz';guest.write_bytes(gzip.compress(data,compresslevel=1,mtime=0))
(out/'manifest.json').write_text(json.dumps({'revision':args.revision,'level':args.level,
    'rootfs_bytes':squash.stat().st_size,'rootfs_sha256':hashlib.sha256(squash.read_bytes()).hexdigest(),
    'guest_sha256':hashlib.sha256(guest.read_bytes()).hexdigest(),'real_asus_rc_executed':False},indent=2)+'\n')
print('COMPAT_GUEST_PACKED',args.revision,squash.stat().st_size)
