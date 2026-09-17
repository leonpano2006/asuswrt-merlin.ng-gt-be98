#!/usr/bin/env python3
"""Publish replay code and reviewed evidence, excluding binaries and live credentials."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

r = Path(__file__).resolve().parents[1]
out = r / 'publish'
assert not out.exists()
dest = out / 'gt-be98/userspace/userspace-refresh'
paths = [r / n for n in ['README.md', 'UPDATES.md', 'result.json']]
for directory in ['scripts', 'configs', 'tests']:
    paths += [p for p in (r / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [r / 'evidence' / name for name in ['elf-inventory.json', 'openssl4-build.json',
    'openssl4-overlay.json', 'openssl4-commands.json', 'openssl4-upstream-tests.json',
    'systemd-openssl4-build.json', 'systemd-openssl4-commands.json', 'systemd-openssl4-native-test.json',
    'size-probe.json', 'overlay-preservation.json', 'upstream-index.json']]
paths += [r / 'sources/source-records.json', r / 'builds/qemu/crypto-v2/result.json']
for source in paths:
    target = dest / source.relative_to(r)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
files = {}
for path in out.rglob('*'):
    if not path.is_file(): continue
    data = path.read_bytes()
    assert not data.startswith(b'\x7fELF') and len(data) < 1_000_000
    assert not any(line.startswith(b'-----BEGIN ') and b'PRIVATE KEY-----' in line for line in data.splitlines())
    files[path.relative_to(out).as_posix()] = hashlib.sha256(data).hexdigest()
archive = r / 'publication.tar'
with tarfile.open(archive, 'w') as tar:
    for name in sorted(files): tar.add(out / name, arcname=name)
record = {'files': files, 'tar_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}
(r / 'publication-manifest.json').write_text(json.dumps(record, indent=2) + '\n')
print('PUBLICATION_FILES', len(files))
