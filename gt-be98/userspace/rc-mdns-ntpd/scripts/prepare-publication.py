#!/usr/bin/env python3
"""Allowlist real firmware source, replay code and public verification records."""
from pathlib import Path
import json, shutil, tarfile
from common import sha
r=Path(__file__).resolve().parents[1];w=r.parent
out=r/'publish';out.mkdir(exist_ok=False)
dest=out/'gt-be98/userspace/rc-mdns-ntpd';dest.mkdir(parents=True)
paths=[r/'README.md',r/'OWNERSHIP.md']
for directory in ('scripts','configs','src','units','tests','patches'):
    paths.extend(p for p in (r/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
paths.extend((r/'saved-inputs').glob('*.c'))
paths.extend((r/'saved-inputs').glob('*.h'))
for name in ('rc-build.json','helper-build.json','external-inputs.json','production-delta.json',
             'rc.stripped-elf.txt','leon-service-exec-elf.txt','rc-compiler-switches.txt',
             'compile-warning-comparison.json','development-findings.json','packaging.json','router-readonly-capacity.txt'):
    paths.append(r/'evidence'/name)
paths.extend((r/'candidate').glob('*.manifest.json'))
for source in paths:
    target=dest/source.relative_to(r);target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
for name in ('services.c','ntpd.c','rc-services.c','rc-services.h'):
    source=w/'rmerlin-integration-20260916/source-tree/release/src/router/rc'/name
    assert sha(source)==sha(r/'src'/name)
    target=out/'release/src/router/rc'/name;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
initrd=None
for label in ('network-services-v5','network-services-v5-services','network-services-v5-new'):
    source=r/'builds/qemu'/label/'result.json';result=json.loads(source.read_text())
    assert result['tests_complete'] and result['guest_complete'] and not result['panic']
    if initrd:assert result['initramfs_sha256']==initrd
    initrd=result['initramfs_sha256']
    target=dest/'evidence/qemu'/label/'result.json';target.parent.mkdir(parents=True)
    shutil.copy2(source,target)
files={}
for p in out.rglob('*'):
    if not p.is_file():continue
    data=p.read_bytes();assert not data.startswith(b'\x7fELF') and len(data)<1000000
    assert not any(line.startswith(b'-----BEGIN ') and b'PRIVATE KEY-----' in line for line in data.splitlines())
    files[p.relative_to(out).as_posix()]=sha(p)
archive=r/'publication.tar'
with tarfile.open(archive,'w') as tar:
    for name in sorted(files):tar.add(out/name,arcname=name)
(r/'publication-manifest.json').write_text(json.dumps({'files':files,'tar_sha256':sha(archive)},indent=2)+'\n')
print('REVIEWABLE_PUBLICATION_PREPARED',len(files))
