#!/usr/bin/env python3
"""Publish code, configuration and receipts; keep binaries/raw logs in backups."""
import json, tarfile
from pathlib import Path
from common import sha
r=Path(__file__).resolve().parents[1];prefix='gt-be98/userspace/systemd-features'
assert json.loads((r/'result.json').read_text())['status']=='offline-validated candidate; not flashed'
files=[]
for name in ('README.md','result.json','backup-manifest.json','scripts','configs','tests','live'):
    p=r/name
    files += [p] if p.is_file() else [f for f in p.rglob('*') if f.is_file() and '__pycache__' not in str(f)]
files=[p for p in files if p.name!='prepare-root.py']
files += list((r/'evidence').glob('*.json'))
files += [r/'evidence'/n for n in ('systemd-version.txt','live-sysctl.txt','live-readonly-final.txt','live-bootstate-unchanged.txt')]
files += list((r/'candidate').glob('*.manifest.json'))
files += list((r/'builds/qemu').glob('*/result.json'))
files += [r/'build/features-v3/production-preservation.json']
manifest={}
with tarfile.open(r/'publication.tar','w') as archive:
    for p in sorted(set(files)):
        assert p.exists(),p
        # All selected text remains byte-identical; raw console logs stay in the backup.
        name=prefix+'/'+p.relative_to(r).as_posix()
        archive.add(p,arcname=name,recursive=False)
        manifest[name]=sha(p)
(r/'publication-manifest.json').write_text(json.dumps({'files':manifest,'tar_sha256':sha(r/'publication.tar')},indent=2)+'\n')
print('PUBLICATION_FILES',len(manifest))
