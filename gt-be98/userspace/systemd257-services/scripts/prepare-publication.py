#!/usr/bin/env python3
"""Public allowlist only: code, replay inputs, hashes and offline test records."""
from pathlib import Path
import json,shutil,tarfile
from common import sha
r=Path(__file__).resolve().parents[1];w=r.parent;out=r/'publish';out.mkdir(exist_ok=False)
dest=out/'gt-be98/userspace/systemd257-services';dest.mkdir(parents=True)
for name in ('services.c','rc-services.c','rc-services.h'):
    rel=Path('release/src/router/rc')/name;p=out/rel;p.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(w/'rmerlin-integration-20260916/source-tree'/rel,p)
for folder in ('src','scripts','configs','tests','units','patches'):
    for p in (r/folder).rglob('*'):
        if not p.is_file() or '__pycache__' in p.parts:continue
        target=dest/p.relative_to(r);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
for name in ('README.md','OWNERSHIP.md','PODMAN.md'):
    shutil.copy2(r/name,dest/name)
for p in (r/'saved-inputs').glob('*'):
    if p.suffix not in ('.c','.h'):continue
    target=dest/'saved-inputs'/p.name;target.parent.mkdir(exist_ok=True);shutil.copy2(p,target)
for p in list((r/'evidence').glob('*.json'))+list((r/'candidate').glob('*.manifest.json')):
    target=dest/'evidence'/p.name;target.parent.mkdir(exist_ok=True);shutil.copy2(p,target)
for label in ('systemd257-v5','services257-v5'):
    for name in ('result.json','serial.log'):
        p=r/'builds/qemu'/label/name;target=dest/'evidence/qemu'/label/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
for p in out.rglob('*'):
    if not p.is_file():continue
    data=p.read_bytes()
    assert not data.startswith(b'\x7fELF') and len(data)<3_000_000,p
    assert not any(line.startswith(b'-----BEGIN ') and b'PRIVATE KEY-----' in line for line in data.splitlines()),p
files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}
archive=r/'publication.tar'
with tarfile.open(archive,'w') as tar:
    for name in sorted(files):tar.add(out/name,arcname=name)
(r/'publication-manifest.json').write_text(json.dumps({'files':files,'tar_sha256':sha(archive)},indent=2)+'\n')
print('PUBLICATION_PREPARED',len(files),'files;',archive.stat().st_size,'bytes')
