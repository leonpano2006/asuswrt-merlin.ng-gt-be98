#!/usr/bin/env python3
"""Archive this delta, a standalone QEMU replay, and the candidate image."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
import tarfile
from common import sha

r = Path(__file__).resolve().parents[1]; w = r.parent
final = json.loads((r / 'completed.json').read_text())
assert final['offline_tests_passed'] and not final['flashed']
replay = r / 'replay'; replay.mkdir(exist_ok=False)
shutil.copy2(w / 'multiarch-loader-20260916/saved-inputs/Image36', replay / 'Image36')
shutil.copy2(r / 'build' / final['rehearsal'] / 'guest.cpio.gz', replay / 'guest.cpio.gz')
files = set()
for folder in ('src', 'scripts', 'tests', 'units', 'patches', 'configs', 'evidence',
               'saved-inputs', 'builds/qemu', 'candidate', 'build/rc', 'build/probes', 'replay'):
    for directory, dirs, names in os.walk(r / folder, followlinks=False):
        dirs[:] = [x for x in dirs if x != '__pycache__']
        files.update(Path(directory) / x for x in names)
files.update(r / name for name in ('README.md', 'OWNERSHIP.md', 'completed.json'))
files.update(r / 'sources/rc' / name for name in ('services.c', 'Makefile', 'rc-services.c', 'rc-services.h'))
rows = {}
for p in sorted(files):
    st = p.lstat(); assert stat.S_ISREG(st.st_mode), p
    rows[str(p.relative_to(r))] = {'mode': stat.S_IMODE(st.st_mode), 'bytes': st.st_size, 'sha256': sha(p)}
manifest = {'files': rows, 'parent': json.loads((r / 'configs/parent.json').read_text()),
    'restoration': 'Replay needs only replay/Image36, guest.cpio.gz and QEMU. Rebuild needs the pinned trial3 and compiler/BSP archives.'}
# Retain the common verifier format used by the previous immutable checkpoint backups.
mp = r / 'postflash-manifest.json'; mp.write_text(json.dumps(manifest, indent=2) + '\n')
archive = r / 'systemd-service-split-backup.tar'
with tarfile.open(archive, 'x') as out:
    for p in sorted(files | {mp}):
        out.add(p, arcname=r.name + '/' + str(p.relative_to(r)), recursive=False)
with tarfile.open(archive) as source:
    for name, row in rows.items():
        member = source.getmember(r.name + '/' + name)
        assert member.isfile() and member.mode == row['mode'] and member.size == row['bytes']
        with source.extractfile(member) as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256'], name
receipt = {'archive': archive.name, 'bytes': archive.stat().st_size,
           'sha256': sha(archive), 'verified_members': len(rows), 'flashed': False}
(r / 'backup-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
