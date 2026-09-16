#!/usr/bin/env python3
"""Save final source and trial evidence as a supplement to the immutable preflash backup."""
from pathlib import Path
import hashlib
import json
import os
import stat
import tarfile
from common import sha

r = Path(__file__).resolve().parents[1]
files = set()
for folder in ('scripts', 'src', 'tests', 'units', 'patches', 'configs', 'evidence', 'flash', 'builds/qemu'):
    for directory, dirs, names in os.walk(r / folder, followlinks=False):
        dirs[:] = [x for x in dirs if x != '__pycache__']
        files.update(Path(directory) / x for x in names if x != '__pycache__')
files.update(r / name for name in ('README.md', 'completed.json', 'preflash-receipt.json',
                                   'ml350-preflash-receipt.json'))
files.update((r / 'candidate').glob('*.json'))
rows = {}
for p in sorted(files):
    st = p.lstat()
    assert stat.S_ISREG(st.st_mode), p
    rows[str(p.relative_to(r))] = {'mode': stat.S_IMODE(st.st_mode),
                                  'bytes': st.st_size, 'sha256': sha(p)}
manifest = {'base_archive': json.loads((r / 'preflash-receipt.json').read_text()),
            'files': rows,
            'restoration': 'Restore the preflash archive first, then overlay this checkpoint supplement.'}
manifest_path = r / 'postflash-manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
archive = r / 'systemd-trial3-postflash.tar'
with tarfile.open(archive, 'x') as out:
    for p in sorted(files | {manifest_path}):
        out.add(p, arcname=r.name + '/' + str(p.relative_to(r)), recursive=False)
with tarfile.open(archive) as source:
    for name, row in rows.items():
        member = source.getmember(r.name + '/' + name)
        assert member.isfile() and member.mode == row['mode'] and member.size == row['bytes']
        with source.extractfile(member) as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256'], name
receipt = {'archive': archive.name, 'bytes': archive.stat().st_size,
           'sha256': sha(archive), 'verified_members': len(rows),
           'base_archive_sha256': manifest['base_archive']['sha256']}
(r / 'backup-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
