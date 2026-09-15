#!/usr/bin/env python3
"""Prepare NVRAM fix, GCC 15 libraries, and Ubuntu-style multiarch glibc."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--base-squashfs', type=Path, required=True)
p.add_argument('--patch-script', type=Path, required=True)
p.add_argument('--armel-checkpoint', type=Path, default=Path(__file__).resolve().parents[2]/'armel-multiarch')
p.add_argument('--rebuilt', type=Path, required=True)
p.add_argument('--multiarch-loader-checkpoint', type=Path,
               default=Path(__file__).resolve().parents[2]/'multiarch-loader')
p.add_argument('--glibc-runtime', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--report', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
config = json.loads((root/'candidate.json').read_text())
policy = config['required_postprocessing']
checkpoint = a.armel_checkpoint.resolve(strict=True)
loader_checkpoint = a.multiarch_loader_checkpoint.resolve(strict=True)
loader_policy = config['required_loader_postprocessing']
if a.output.exists() or a.output.is_symlink() or a.report.exists():
    p.error('output and report must be new offline paths')
for name, expected in policy['checkpoint_files'].items():
    if sha(checkpoint/name) != expected:
        p.error('unreviewed checkpoint file: '+name)
for name, expected in policy['tested_libraries'].items():
    if sha(a.rebuilt/name) != expected:
        p.error('rebuilt library differs from the tested candidate: '+name)
for name, expected in loader_policy['checkpoint_files'].items():
    if sha(loader_checkpoint/name) != expected:
        p.error('unreviewed loader checkpoint file: '+name)
if sha(a.glibc_runtime.parent/'runtime-manifest.json') != loader_policy['runtime_manifest_sha256']:
    p.error('glibc runtime differs from the tested candidate')
a.output.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='candidate-base-', dir=a.output.parent) as temp:
    temp = Path(temp)
    subprocess.run([sys.executable, str(root/'scripts/prepare-base-rootfs.py'),
                    '--base-squashfs', str(a.base_squashfs), '--patch-script', str(a.patch_script),
                    '--output', str(temp/'base'), '--report', str(temp/'base.json')], check=True)
    subprocess.run([sys.executable, str(checkpoint/'scripts/migrate-rootfs.py'),
                    '--source', str(temp/'base'), '--output', str(temp/'armel'),
                    '--report', str(temp/'migration.json')], check=True)
    subprocess.run([sys.executable, str(checkpoint/'scripts/apply-libraries.py'),
                    '--rootfs', str(temp/'armel'), '--rebuilt', str(a.rebuilt),
                    '--policy', str(checkpoint/'configs/library-overlay.json'),
                    '--report', str(temp/'libraries.json')], check=True)
    subprocess.run([sys.executable, str(loader_checkpoint/'scripts/prepare-rootfs.py'),
                    '--source', str(temp/'armel'), '--runtime', str(a.glibc_runtime),
                    '--output', str(a.output), '--report', str(temp/'loader.json')], check=True)
    report = {'candidate': config['candidate'], 'status': 'complete-rootfs-prepared-for-packaging',
              'base': json.loads((temp/'base.json').read_text()),
              'migration': json.loads((temp/'migration.json').read_text()),
              'rebuilt_libraries': json.loads((temp/'libraries.json').read_text()),
              'multiarch_loader': json.loads((temp/'loader.json').read_text()),
              'firmware_packaged': False, 'router_modified': False,
              'firmware_commit_performed': False}
a.report.parent.mkdir(parents=True, exist_ok=True)
a.report.write_text(json.dumps(report, indent=2)+'\n')
print('Complete candidate rootfs prepared:', a.output)
