#!/usr/bin/env python3
"""Enumerate in-tree hard-float ELF objects without executing them."""
import json
from pathlib import Path
from elftools.elf.elffile import ELFFile
r=Path(__file__).resolve().parents[1];root=r.parent/'rootfs-slim-20260917/build/optimized-rootfs';found=[]
for p in root.rglob('*'):
 if p.is_symlink() or not p.is_file():continue
 with p.open('rb') as f:
  if f.read(4)!=b'\x7fELF':continue
  f.seek(0);e=ELFFile(f)
  interp=[s.get_interp_name() for s in e.iter_segments() if s.header.p_type=='PT_INTERP']
  if e.header.e_machine=='EM_ARM' and (e.header.e_flags&0x400 or any('armhf' in s for s in interp)):
   d=e.get_section_by_name('.dynamic')
   found.append({'path':str(p.relative_to(root)),'flags':hex(e.header.e_flags),'interp':interp,
                 'needed':[t.needed for t in d.iter_tags() if t.entry.d_tag=='DT_NEEDED'] if d else []})
assert all(x['path'].startswith('usr/lib/arm-linux-gnueabihf/') for x in found)
(r/'evidence/armhf-consumers.json').write_text(json.dumps(found,indent=2)+'\n')
print('ARMHF_ELFS',len(found),'OUTSIDE_LIBRARY_DIRECTORY',0)
