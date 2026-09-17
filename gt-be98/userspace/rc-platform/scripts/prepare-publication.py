"""Publish actual C edits and reproducible checkpoint sources without raw blobs."""
import json,tarfile
from pathlib import Path
from common import sha
r=Path(__file__).resolve().parents[1];prefix='gt-be98/userspace/rc-platform'
assert json.loads((r/'result.json').read_text())['status']=='offline-validated candidate; not flashed'
files=[]
for name in ('README.md','result.json','backup-manifest.json','scripts','configs','tests','src','units','patches'):
 p=r/name;files += [p] if p.is_file() else [f for f in p.rglob('*') if f.is_file() and '__pycache__' not in str(f)]
files+=list((r/'evidence').glob('*.json'))+[r/'evidence/build-ids.txt']+list((r/'candidate').glob('*.manifest.json'))+list((r/'builds/qemu').glob('*/result.json'))+[r/'build/platform-v7/production-preservation.json']
manifest={};names=('services.c','usb.c','rc-services.c','rc-services.h')
with tarfile.open(r/'publication.tar','w') as archive:
 for p in sorted(set(files)):
  assert p.exists(),p
  name=prefix+'/'+p.relative_to(r).as_posix();archive.add(p,arcname=name,recursive=False);manifest[name]=sha(p)
 for n in (*names,'leon-daemons.h','leon-daemon-supervisor.c'):
  name='release/src/router/rc/'+n;archive.add(r/'src'/n,arcname=name,recursive=False);manifest[name]=sha(r/'src'/n)
(r/'publication-manifest.json').write_text(json.dumps({'files':manifest,'base_rc_files':{n:sha(r/'saved-inputs'/n) for n in names},'tar_sha256':sha(r/'publication.tar')},indent=2)+'\n')
print('PUBLICATION_FILES',len(manifest))
