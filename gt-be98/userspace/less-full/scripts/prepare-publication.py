#!/usr/bin/env python3
"""Publish replay code and public evidence, excluding live logs and binaries."""
from pathlib import Path
import json
import shutil
import tarfile
from common import sha

r = Path(__file__).resolve().parents[1]
out = r / 'publish'
out.mkdir(exist_ok=False)
dest = out / 'gt-be98/userspace/less-full'
dest.mkdir(parents=True)
paths = [r / 'README.md', r / 'live/apply-live.sh', r / 'live/pager-profile.sh']
for folder in ('scripts', 'configs'):
    paths.extend(p for p in (r / folder).rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts)
paths.extend((r / 'saved-inputs').glob('*.h'))
for name in ('build.json', 'rootfs-changes.json', 'live-tests.json',
             'packaging.json', 'compiler-switches.txt', 'source-signature.txt',
             'less-elf.txt', 'lesskey-elf.txt', 'lessecho-elf.txt'):
    paths.append(r / 'evidence' / name)
paths.extend((r / 'evidence').glob('layout-*.json'))
paths.extend((r / 'candidate').glob('*.manifest.json'))
for path in paths:
    target = dest / path.relative_to(r)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
for label in ('less704-systemd257', 'less704-services257'):
    source = r / 'builds/qemu' / label / 'result.json'
    record = json.loads(source.read_text())
    assert record['tests_complete'] and record['guest_complete'] and not record['panic']
    target = dest / 'evidence/qemu' / label / 'result.json'
    target.parent.mkdir(parents=True)
    shutil.copy2(source, target)
for path in out.rglob('*'):
    if not path.is_file():
        continue
    data = path.read_bytes()
    assert not data.startswith(b'\x7fELF')
    assert not any(line.startswith(b'-----BEGIN ') and b'PRIVATE KEY-----' in line
                   for line in data.splitlines())
    assert len(data) < 1_000_000
files = {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()}
archive = r / 'publication.tar'
with tarfile.open(archive, 'w') as tar:
    for name in sorted(files):
        tar.add(out / name, arcname=name)
(r / 'publication-manifest.json').write_text(json.dumps({
    'files': files, 'tar_sha256': sha(archive)}, indent=2) + '\n')
print('PUBLICATION_PREPARED', len(files), 'files')
