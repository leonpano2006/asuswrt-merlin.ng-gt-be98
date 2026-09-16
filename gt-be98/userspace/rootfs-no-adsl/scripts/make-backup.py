#!/usr/bin/env python3
"""Archive the selected candidate and exact external reproduction inputs."""
import hashlib
import json
from pathlib import Path
import tarfile

r = Path(__file__).resolve().parents[1]
w = r.parent
output = r / 'rootfs-no-adsl-backup.tar'
assert not output.exists()
paths = []
for folder in ('scripts', 'configs', 'evidence', 'candidate', 'builds/qemu/no-adsl-zstd22-1m-tailends'):
    paths += [p for p in (r / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [r / name for name in ('README.md', 'completed.json', 'build/zstd22-1m-tailends.squashfs', 'build/guest.cpio.gz')]
paths += [w / name for name in (
    'a53-runtimes-20260916/build/rootfs.squashfs',
    'a53-runtimes-20260916/build/guest.cpio.gz',
    'a53-runtimes-20260916/flash/GT-BE98_leon36-a53-runtimes_zstd22.pkgtb',
    'multiarch-loader-20260916/saved-inputs/Image36',
        'storage-layout-20260916/evidence/summary.json',
    'leon-cgroup-20260915/archive/worktree/release/src-rt-5.04behnd.4916/targets/96813GW/fs/rom/etc/adsl1/adsl_phy.bin',
    'leon-cgroup-20260915/archive/worktree/release/src-rt-5.04behnd.4916/targets/96813GW/fs.install/rom/etc/adsl1/adsl_phy.bin',
    'leon-cgroup-20260915/archive/worktree/release/src-rt-5.04behnd.4916/make.common',
    'leon-cgroup-20260915/archive/worktree/release/src-rt-5.04behnd.4916/bcmdrivers/opensource/net/enet/impl7/runner.c')]
def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()
manifest = {str(p.relative_to(w)): sha(p) for p in sorted(set(paths))}
manifest_path = r / 'backup-manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
with tarfile.open(output, 'w') as t:
    for p in sorted(set(paths + [manifest_path])):
        t.add(p, arcname=p.relative_to(w), recursive=False)
with tarfile.open(output) as t:
    for name, expected in manifest.items():
        with t.extractfile(name) as f:
            assert hashlib.file_digest(f, 'sha256').hexdigest() == expected, name
receipt = {'archive': output.name, 'bytes': output.stat().st_size,
           'sha256': sha(output), 'verified_members': len(manifest),
           'includes_exact_original_rootfs_image': True,
           'includes_original_and_selected_qemu_inputs': True,
           'includes_original_pkgtb_and_candidate': True,
           'unpacked_source_restore': 'Extract the saved original rootfs.squashfs to a53-runtimes-20260916/build/unpacked-rootfs with unsquashfs, preserving mode/link/mtime.',
           'includes_only_selected_no_adsl_candidate': True}
(r / 'backup-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2), flush=True)
