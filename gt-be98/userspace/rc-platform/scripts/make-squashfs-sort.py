#!/usr/bin/env python3
"""Measure lossless file ordering by ELF family, basename or size."""
from pathlib import Path
import argparse,json
policy=Path(__file__).resolve().parents[1]/'configs/squashfs-sort.json'
default=json.loads(policy.read_text())['strategy'] if policy.exists() else 'type-size'
p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path)
p.add_argument('--strategy',choices=['type-size','systemd-first','systemd-last','family-name','family-size-up','path'],default=default);a=p.parse_args()
files=[]
for f in a.root.rglob('*'):
 if not f.is_file() or f.is_symlink():continue
 with f.open('rb') as stream:header=stream.read(20)
 kind='elf-'+str(int.from_bytes(header[18:20],'little')) if header[:4]==b'\x7fELF' else f.suffix.lower() or 'text'
 name=f.relative_to(a.root).as_posix();assert '\n' not in name and '\t' not in name
 if kind=='elf-183' and a.strategy not in ('type-size','path'):
  family='/systemd/' in name or f.name in ('systemctl','journalctl','systemd-notify','systemd-run')
  kind+='-'+str(int(family) if a.strategy=='systemd-last' else int(not family))
 if a.strategy=='family-name': key=(kind,f.name,name)
 elif a.strategy=='family-size-up': key=(kind,f.stat().st_size,name)
 elif a.strategy=='path': key=('',name,name)
 else:key=(kind,-f.stat().st_size,name)
 files.append(key)
assert len(files)<64000
rows=sorted(files)
a.output.write_text(''.join(name.replace(' ','\\ ')+' '+str(32000-i)+'\n' for i,(_,_,name) in enumerate(rows)))
