#!/usr/bin/env python3
"""Archive exact new inputs/results; parent checkpoints are backed up separately."""
from pathlib import Path
import hashlib
import json
import subprocess
import tarfile
from common import sha

r = Path(__file__).resolve().parents[1]
archive = r / 'less704-checkpoint.tar.zst'
assert not archive.exists()
selected = []
for folder in ('scripts', 'configs', 'live', 'saved-inputs', 'sources', 'sdk',
               'stage', 'evidence', 'candidate', 'builds'):
    selected.extend(p for p in (r / folder).rglob('*')
                    if p.is_file() or p.is_symlink())
for folder in ('obj', 'live-payload'):
    selected.extend(p for p in (r / 'build' / folder).rglob('*')
                    if p.is_file() or p.is_symlink())
for name in ('README.md', 'completed-candidate.json', 'build/cc', 'build/run-target', 'build/live-payload.tar',
             'build/less704-systemd257/guest.cpio.gz',
             'build/less704-systemd257/production-preservation.json',
             'publication.tar', 'publication-manifest.json'):
    selected.append(r / name)
selected = sorted(set(p for p in selected if '__pycache__' not in p.parts))
manifest = {}
for p in selected:
    row = {'mode': p.lstat().st_mode & 0o7777}
    if p.is_symlink():
        row['link'] = p.readlink().as_posix()
    else:
        row.update(sha256=sha(p), bytes=p.stat().st_size)
    manifest[p.relative_to(r).as_posix()] = row
with archive.open('xb') as output:
    compressor = subprocess.Popen(['zstd', '-T4', '-5', '--long=27', '-c'],
                                  stdin=subprocess.PIPE, stdout=output)
    with tarfile.open(fileobj=compressor.stdin, mode='w|') as tar:
        for p in selected:
            tar.add(p, arcname=p.relative_to(r).as_posix(), recursive=False)
    compressor.stdin.close()
    assert compressor.wait() == 0
archive.chmod(0o600)
decompressor = subprocess.Popen(['zstd', '-dc', str(archive)], stdout=subprocess.PIPE)
seen = set()
with tarfile.open(fileobj=decompressor.stdout, mode='r|') as tar:
    for member in tar:
        assert member.name not in seen
        seen.add(member.name)
        row = manifest[member.name]
        assert member.mode == row['mode']
        if member.issym():
            assert member.linkname == row['link']
        elif member.islnk():
            assert member.linkname in seen and member.linkname != member.name
            original = manifest[member.linkname]
            assert original['sha256'] == row['sha256']
            assert original['bytes'] == row['bytes']
        else:
            assert member.isfile() and member.size == row['bytes']
            assert hashlib.file_digest(tar.extractfile(member), 'sha256').hexdigest() == row['sha256']
assert decompressor.wait() == 0
assert seen == manifest.keys()
(r / 'backup-members.json').write_text(json.dumps(manifest, indent=2) + '\n')
record = {'archive': archive.name, 'bytes': archive.stat().st_size,
          'sha256': sha(archive), 'verified_members': len(seen),
          'requires_parent_checkpoint': 'systemd-upgrade-20260917/preflash-final.tar.zst'}
(r / 'backup-receipt.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
