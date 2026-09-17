#!/usr/bin/env python3
"""Measure a read-only source tree using the existing kernel's supported format."""
import argparse, hashlib, json, subprocess, time
from pathlib import Path
r = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('root',type=Path);p.add_argument('label')
p.add_argument('--strategy',default='family-name')
p.add_argument('--zstd157',action='store_true')
a = p.parse_args()
assert all(c.isalnum() or c in '-_' for c in a.label)
sort = r/'build'/f'{a.label}.sort'
out = r/'build'/f'{a.label}.squashfs'
assert not out.exists()
subprocess.run(['python3',str(r.parent/'systemd-rc-next-20260917/scripts/make-squashfs-sort.py'),str(a.root),str(sort),'--strategy',a.strategy],check=True)
cmd = ['mksquashfs',str(a.root),str(out),'-noappend','-all-root','-comp','zstd',
       '-Xcompression-level','22','-b','1048576','-tailends','-sort',str(sort),
       '-processors','4','-mem','512M','-no-progress','-exit-on-error','-mkfs-time','1789560000']
if a.zstd157:
    sdk = r.parent/'userspace-refresh-20260917/sdk'
    zlib = r/'build/packer-lib'
    zlib.mkdir(exist_ok=True)
    link = zlib/'libzstd.so.1'
    if not link.exists():
        link.symlink_to(r.parent/'userspace-refresh-20260917/build/size-probe-rootfs/usr/lib/aarch64-linux-gnu/libzstd.so.1.5.7')
    prefix = [str(sdk/'lib/ld-linux-aarch64.so.1'),'--library-path',
              ':'.join(map(str,[zlib,sdk/'lib/aarch64-linux-gnu',Path('/lib/aarch64-linux-gnu')]))]
    cmd[0] = '/usr/bin/mksquashfs'
    cmd = prefix + cmd
    (r/'evidence'/f'{a.label}-linker.txt').write_text(subprocess.check_output(
        prefix + ['--list','/usr/bin/mksquashfs'],text=True))
start = time.monotonic()
with (r/'evidence'/f'{a.label}.log').open('w') as log:
    subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
size = out.stat().st_size
record = {'label':a.label,'command':cmd,'rootfs_bytes':size,
          'saving_vs_full_openssl_o2_bytes':81633280-size,
          'slot1_limit_bytes':78565376,'headroom_bytes':78565376-size,
          'elapsed_seconds':time.monotonic()-start,
          'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
          'firmware_generated':False,'router_modified':False}
(r/'evidence'/f'{a.label}.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='command'},indent=2))
