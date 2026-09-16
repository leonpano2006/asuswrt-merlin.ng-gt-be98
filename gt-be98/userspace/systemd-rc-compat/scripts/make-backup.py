#!/usr/bin/env python3
"""Save code, exact retained RC objects/headers and only the final large guest."""
from pathlib import Path
import hashlib
import json
import os
import stat
import tarfile
from common import sha

r = Path(__file__).resolve().parents[1]
w = r.parent
output = r / 'systemd-rc-compat-backup.tar'
assert not output.exists(), output
paths = set()
for folder in ('scripts', 'src', 'tests', 'units', 'patches', 'configs', 'evidence',
               'overlay', 'sources/rc', 'saved-inputs', 'build/rc', 'build/probes', 'builds/qemu'):
    root = r / folder
    paths.add(root)
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        paths.update(Path(directory) / name for name in dirs + files if name != '__pycache__')
paths.update(r / name for name in ('README.md', 'completed.json',
    'build/guarded-final/rootfs.squashfs', 'build/guarded-final/guest.cpio.gz',
    'build/guarded-final/manifest.json', 'build/guarded-final/squashfs.log',
    'build/libxcrypt/config.log', 'build/libxcrypt/config.status'))
paths.update(w / name for name in ('multiarch-loader-20260916/saved-inputs/Image36',
    'systemd-lab-20260916/ml350-backup-receipt.json', 'systemd-lab-20260916/configs/sources.json',
    'systemd-lab-20260916/downloads/libxcrypt-4.4.38.tar.gz',
    'a53-runtimes-20260916/configs/build-targets.json'))
manifest = {}
for p in sorted(paths):
    st = p.lstat()
    row = {'mode': stat.S_IMODE(st.st_mode)}
    if p.is_symlink():
        row.update(kind='link', target=os.readlink(p))
    elif p.is_dir():
        row['kind'] = 'directory'
    else:
        assert stat.S_ISREG(st.st_mode), p
        row.update(kind='file', bytes=st.st_size, sha256=sha(p))
    manifest[str(p.relative_to(w))] = row
manifest_path = r / 'backup-manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
with tarfile.open(output, 'x', dereference=False) as archive:
    for p in sorted(paths | {manifest_path}):
        archive.add(p, arcname=p.relative_to(w), recursive=False)
with tarfile.open(output) as archive:
    for name, row in manifest.items():
        member = archive.getmember(name)
        assert member.mode == row['mode'], name
        if row['kind'] == 'file':
            with archive.extractfile(member) as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256'], name
        elif row['kind'] == 'link':
            assert member.issym() and member.linkname == row['target'], name
        else:
            assert member.isdir(), name
receipt = {'archive': output.name, 'bytes': output.stat().st_size, 'sha256': sha(output),
    'verified_members': len(manifest), 'includes_code_patch_rc_objects_headers_final_guest': True,
    'external_dependencies': 'evidence/build-dependencies.json', 'router_modified': False}
(r / 'backup-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
