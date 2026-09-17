#!/usr/bin/env python3
import hashlib,json,tarfile
from pathlib import Path
r=Path(__file__).resolve().parents[1];prefix='gt-be98/userspace/armhf-release'
files=[]
for name in ['README.md','result.json','scripts','configs','flash/scripts','flash/evidence','flash/expected-files.json','builds/qemu/armhf-usb-v2/result.json']:
 p=r/name
 files+=([p] if p.is_file() else [f for f in p.rglob('*') if f.is_file() and '__pycache__' not in str(f)])
for pattern in ['*-oz-commands.json','final-*','qemu-verification.json','zstd-build.json','zstd-tests.json','sqlite-build.json','sqlite-tests.json']:
 files += list((r/'evidence').glob(pattern))
files += list((r/'candidate').glob('*.manifest.json'))
files=sorted(set(files))
manifest={}
with tarfile.open(r/'publication.tar','w') as t:
 for f in files:
  name=prefix+'/'+f.relative_to(r).as_posix();t.add(f,arcname=name,recursive=False);manifest[name]=hashlib.sha256(f.read_bytes()).hexdigest()
(r/'publication-manifest.json').write_text(json.dumps({'files':manifest,'tar_sha256':hashlib.sha256((r/'publication.tar').read_bytes()).hexdigest()},indent=2)+'\n')
print('PUBLICATION_FILES',len(files))
