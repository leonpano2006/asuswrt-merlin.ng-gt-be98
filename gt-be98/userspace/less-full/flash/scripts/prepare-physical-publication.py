#!/usr/bin/env python3
"""Public code/results allowlist; raw live journals and terminal logs stay private."""
from pathlib import Path
import hashlib
import json
import shutil
import tarfile

r = Path(__file__).resolve().parents[2]
out = r / 'postflash-publish'
shutil.copytree(r / 'publish', out)
dest = out / 'gt-be98/userspace/less-full'
shutil.copy2(r / 'README.md', dest / 'README.md')
scripts = dest / 'flash/scripts'
scripts.mkdir(parents=True)
for p in (r / 'flash/scripts').iterdir():
    if p.is_file() and p.suffix in ('.py', '.sh', '.bash'):
        shutil.copy2(p, scripts / p.name)
evidence = dest / 'flash/evidence'
evidence.mkdir()
names = ['trial-result.json', 'discovery.json', 'web-check.json',
         'docker-lan.json', 'https-management.json', 'live-tests.json',
         'verify-written.txt', 'ram-acceptance.txt', 'cron-live.txt',
         'acceleration-stable-flows.txt', 'live-upstream.txt',
         'docker-memcg-and-httpd.txt']
for name in names:
    shutil.copy2(r / 'flash/evidence' / name, evidence / name)
record = json.loads((evidence / 'trial-result.json').read_text())
assert record['physical_pass'] and record['readback_pass']
assert record['commit_flags'] == [0, 1]
files = {}
for p in out.rglob('*'):
    if not p.is_file():
        continue
    data = p.read_bytes()
    assert not data.startswith(b'\x7fELF') and len(data) < 1_000_000
    assert not any(x.startswith(b'-----BEGIN ') and b'PRIVATE KEY-----' in x
                   for x in data.splitlines())
    files[p.relative_to(out).as_posix()] = hashlib.sha256(data).hexdigest()
archive = r / 'flash/publication.tar'
with tarfile.open(archive, 'w') as tar:
    for name in sorted(files):
        tar.add(out / name, arcname=name)
(r / 'flash/publication-manifest.json').write_text(json.dumps({
    'files': files, 'tar_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}, indent=2) + '\n')
print('PHYSICAL_PUBLICATION_PREPARED', len(files))
