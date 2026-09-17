#!/usr/bin/env python3
"""Check unpacked content and let the exact #36 kernel read every packed file."""
import gzip, hashlib, json, stat, subprocess, sys
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent
sys.path.insert(0,str(w/'multiarch-loader-20260916/scripts'))
from common import inventory
source=w/'userspace-refresh-20260917/build/size-probe-rootfs'
image=r/'build/packer-zstd157.squashfs'
unpacked=r/'build/packer-zstd157-unpacked'
assert not unpacked.exists()
with (r/'evidence/unpack.log').open('w') as log:
    subprocess.run(['unsquashfs','-no-progress','-processors','4','-d',str(unpacked),str(image)],stdout=log,stderr=subprocess.STDOUT,check=True)
expected=inventory(source);assert inventory(unpacked)==expected
raw=gzip.decompress((w/'a53-runtimes-20260916/build/guest.cpio.gz').read_bytes())
p=0;busybox=None
while p<len(raw):
    f=[int(raw[p+6+8*i:p+14+8*i],16) for i in range(13)]
    name=raw[p+110:p+109+f[11]].decode();start=(p+110+f[11]+3)&~3
    if name=='bin/busybox':busybox=raw[start:start+f[6]];break
    p=(start+f[6]+3)&~3
assert busybox
entries={d:(stat.S_IFDIR|0o755,b'',0,0) for d in ['bin','dev','proc','sys','tmp','newroot']}
checks=''.join(row['sha256']+'  /newroot/'+name+'\n' for name,row in sorted(expected.items()) if row['kind']=='file')
init=b'''#!/bin/busybox sh
set -eu
export PATH=/bin
/bin/busybox --install -s /bin
exec </dev/console >/dev/console 2>&1
echo QEMU_LAB_INIT_REACHED
trap 'echo PACKING_FAILED; poweroff -f' EXIT
mount -t proc proc /proc
mount -t sysfs sysfs /sys
losetup -r /dev/loop0 /rootfs.squashfs
mount -t squashfs -o ro /dev/loop0 /newroot
if ! sha256sum -c /files.sha256 >/tmp/check.log 2>&1; then
    grep -v ': OK$' /tmp/check.log
    exit 1
fi
echo LAB_SQUASHFS_ALL_FILES_PASS
trap - EXIT
poweroff -f
'''
entries.update({'bin/busybox':(stat.S_IFREG|0o755,busybox,0,0),'init':(stat.S_IFREG|0o755,init,0,0),
                'rootfs.squashfs':(stat.S_IFREG|0o444,image.read_bytes(),0,0),
                'files.sha256':(stat.S_IFREG|0o444,checks.encode(),0,0),
                'dev/console':(stat.S_IFCHR|0o600,b'',5,1),
                'dev/loop0':(stat.S_IFBLK|0o600,b'',7,0),'TRAILER!!!':(0,b'',0,0)})
out=bytearray()
for ino,(name,(mode,data,major,minor)) in enumerate(entries.items(),1):
    name=name.encode()+b'\0';fields=[ino,mode,0,0,2 if stat.S_ISDIR(mode) else 1,0,len(data),0,0,major,minor,len(name),0]
    out+=b'070701'+''.join(f'{v:08x}' for v in fields).encode()+name
    out+=b'\0'*(-len(out)%4);out+=data;out+=b'\0'*(-len(out)%4)
guest=r/'build/packing-guest.cpio.gz';guest.write_bytes(gzip.compress(out,compresslevel=1,mtime=0))
runner=(w/'rootfs-size-20260916/scripts/run-qemu.py').read_text()
(r/'scripts/run-packing-qemu.py').write_text(runner)
subprocess.run(['python3',str(r/'scripts/run-packing-qemu.py'),'--label','zstd157',
                '--kernel',str(w/'multiarch-loader-20260916/saved-inputs/Image36'),
                '--initrd',str(guest),'--complete-marker','reboot: Power down','--timeout','120'],check=True)
q=json.loads((r/'builds/qemu/zstd157/result.json').read_text())
assert 'LAB_SQUASHFS_ALL_FILES_PASS' in q['lab_lines']
record={'contents_modes_links_preserved':True,'paths':len(expected),
        'regular_files_read_by_kernel':sum(x['kind']=='file' for x in expected.values()),
        'kernel_sha256':q['kernel_sha256'],'rootfs_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
        'all_hashes_passed_in_qemu':True,'router_modified':False}
(r/'evidence/packing-verification.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
