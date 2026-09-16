#!/usr/bin/env python3
"""Measure lossless file ordering; do not remove content or reduce UBI reserve."""
from pathlib import Path
import argparse,json,subprocess,time
from common import sha
r=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('strategy',choices=['type-size','systemd-first','systemd-last']);a=p.parse_args()
root=r/'build/production-rootfs';out=r/'build'/('layout-'+a.strategy+'.squashfs');assert not out.exists()
sort=out.with_suffix('.sort')
subprocess.run(['python3',str(r/'scripts/make-squashfs-sort.py'),str(root),str(sort),'--strategy',a.strategy],check=True)
cmd=['mksquashfs',str(root),str(out),'-noappend','-all-root','-comp','zstd','-Xcompression-level','22',
    '-b','1048576','-tailends','-sort',str(sort),'-processors','4','-mem','512M','-no-progress','-exit-on-error','-mkfs-time','1789560000']
started=time.monotonic()
with (r/'evidence'/('layout-'+a.strategy+'.log')).open('w') as log:
    subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
record={'strategy':a.strategy,'rootfs_bytes':out.stat().st_size,'sha256':sha(out),
    'elapsed_seconds':round(time.monotonic()-started,2),'command':cmd,
    'reserved_blocks':107+(out.stat().st_size+1048576+126975)//126976,'available_blocks':734}
(r/'evidence'/('layout-'+a.strategy+'.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='command'}))
