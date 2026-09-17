#!/usr/bin/env python3
import json,subprocess,sys,shutil
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent
sys.path.insert(0,str(w/'multiarch-loader-20260916/scripts'))
from common import elf_info
parent=w/'armhf-usb-20260917/build/rootfs';root=r/'build/rootfs'
assert not root.exists();subprocess.run(['cp','-a','--reflink=auto',str(parent),str(root)],check=True)
records={}
for abi,triplet in [('aarch64','aarch64-linux-gnu'),('armel','arm-linux-gnueabi')]:
 p=Path(json.loads((r/'evidence'/f'{abi}-built.json').read_text())['path']);old=parent/'usr/lib'/triplet/p.name
 a,b=elf_info(old),elf_info(p)
 missing={k:v for k,v in a['exports'].items() if k not in b['exports']};changed={k:[v,b['exports'][k]] for k,v in a['exports'].items() if k in b['exports'] and v!=b['exports'][k]}
 records[abi]={'missing':missing,'changed':changed,'added':sorted(set(b['exports'])-set(a['exports'])),'old_symbols':len(a['exports']),'new_symbols':len(b['exports'])}
(r/'evidence/cxx-api-check.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps({k:{'missing':len(v['missing']),'changed':len(v['changed']),'old_symbols':v['old_symbols'],'new_symbols':v['new_symbols']} for k,v in records.items()},indent=2))
assert not any(v['missing'] or v['changed'] for v in records.values())
subprocess.run(['cp','-a',str(r/'overlay')+'/.',str(root)],check=True)
# Existing directory modes must be preserved when applying build output.
for d in (r/'overlay').rglob('*'):
 if d.is_dir() and not d.is_symlink():
  previous=parent/d.relative_to(r/'overlay')
  if previous.is_dir():(root/d.relative_to(r/'overlay')).chmod(previous.stat().st_mode&0o7777)
(r/'scripts/measure.py').write_text((w/'rootfs-slim-20260917/scripts/measure.py').read_text())
subprocess.run(['python3',str(r/'scripts/measure.py'),str(root),'cxx-oz','--zstd157'],check=True)
