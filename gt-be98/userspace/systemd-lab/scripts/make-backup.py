#!/usr/bin/env python3
"""Preserve final lab inputs, output, sources, SDK, code, links and evidence."""
import json
import hashlib
import os
from pathlib import Path
import stat
import tarfile
from common import sha

r = Path(__file__).resolve().parents[1]
w = r.parent
output = r / 'systemd-lab-backup.tar'
assert not output.exists()
paths = set()
for folder in ('scripts', 'configs', 'evidence', 'downloads', 'overlay', 'sdk', 'build/probes', 'builds/qemu'):
    root = r / folder
    paths.add(root)
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        paths.update(Path(directory) / name for name in dirs + files if name != '__pycache__')
paths.update(r / name for name in (
    'README.md', 'completed.json', 'build/cc', 'build/run-target',
    'build/guard-service/systemd-lab.squashfs', 'build/guard-service/guest.cpio.gz'))
paths.update(w / name for name in (
    'rootfs-no-adsl-20260916/build/zstd22-1m-tailends.squashfs',
    'a53-runtimes-20260916/build/guest.cpio.gz',
    'multiarch-loader-20260916/saved-inputs/Image36',
    'a53-runtimes-20260916/dependency-backups.json',
    'a53-runtimes-20260916/backup-verified-ml350.json',
    'a53-runtimes-20260916/configs/build-targets.json',
    'rootfs-no-adsl-20260916/ml350-backup-receipt.json'))
manifest = {}
for p in sorted(paths):
    st = p.lstat()
    row = {'mode': stat.S_IMODE(st.st_mode)}
    if p.is_symlink():
        row.update(kind='link', target=os.readlink(p))
    elif p.is_dir():
        row.update(kind='directory')
    else:
        assert stat.S_ISREG(st.st_mode), p
        row.update(kind='file', bytes=st.st_size, sha256=sha(p))
    manifest[str(p.relative_to(w))] = row
manifest_path = r / 'backup-manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
with tarfile.open(output, 'x', dereference=False) as t:
    for p in sorted(paths | {manifest_path}):
        t.add(p, arcname=p.relative_to(w), recursive=False)
with tarfile.open(output) as t:
    for name, row in manifest.items():
        member = t.getmember(name)
        assert member.mode == row['mode'], name
        if row['kind'] == 'file':
            with t.extractfile(member) as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256'], name
        elif row['kind'] == 'link':
            assert member.issym() and member.linkname == row['target'], name
        else:
            assert member.isdir(), name
receipt = {'archive': output.name, 'bytes': output.stat().st_size, 'sha256': sha(output),
    'verified_members': len(manifest), 'includes_source_archives_scripts_sdk_overlay': True,
    'includes_final_guest_rootfs_and_exact_kernel': True,
    'includes_only_final_large_lab_artifacts': True,
    'full_rebuild_external_dependencies': 'evidence/build-dependencies.json',
    'router_modified': False, 'flashable_package_created': False}
(r / 'backup-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2), flush=True)
