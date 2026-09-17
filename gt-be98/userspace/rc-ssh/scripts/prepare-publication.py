#!/usr/bin/env python3
"""Publish code, configuration and receipts; keep binaries/raw logs in backups."""
import json, tarfile
from pathlib import Path
from common import sha
r=Path(__file__).resolve().parents[1];prefix='gt-be98/userspace/rc-ssh'
assert json.loads((r/'result.json').read_text())['status']=='offline-validated candidate; not flashed'
files=[]
for name in ('README.md','result.json','backup-manifest.json','scripts','configs','tests','src','units','patches'):
    p=r/name
    files += [p] if p.is_file() else [f for f in p.rglob('*') if f.is_file() and '__pycache__' not in str(f)]
files += list((r/'evidence').glob('*.json'))
files += [r/'evidence'/'build-ids.txt']
files += list((r/'candidate').glob('*.manifest.json'))
files += list((r/'builds/qemu').glob('*/result.json'))
files += [r/'build'/n/'production-preservation.json' for n in ('ssh-v1','ssh-v2')]
manifest={}
base_files={n:sha(r/'saved-inputs'/n) for n in ('ssh.c','rc-services.c','rc-services.h')}
with tarfile.open(r/'publication.tar','w') as archive:
    for p in sorted(set(files)):
        assert p.exists(),p
        # All selected text remains byte-identical; raw console logs stay in the backup.
        name=prefix+'/'+p.relative_to(r).as_posix()
        archive.add(p,arcname=name,recursive=False)
        manifest[name]=sha(p)
    for n in base_files:
        name='release/src/router/rc/'+n
        archive.add(r/'src'/n,arcname=name,recursive=False)
        manifest[name]=sha(r/'src'/n)
(r/'publication-manifest.json').write_text(json.dumps({'files':manifest,'base_rc_files':base_files,'tar_sha256':sha(r/'publication.tar')},indent=2)+'\n')
print('PUBLICATION_FILES',len(manifest))
