#!/usr/bin/env python3
"""Apply the pinned Ubuntu multiarch adaptation to a pinned glibc git archive."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
from common import sha

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--archive', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
policy = json.loads((root / 'configs/glibc-source.json').read_text())
patch = root / policy['patch']['file']
assert sha(a.archive) == policy['source_archive_sha256']
assert sha(patch) == policy['patch']['sha256']
assert not a.output.exists() and not a.output.is_symlink()
a.output.mkdir(parents=True)
with tarfile.open(a.archive) as archive:
    archive.extractall(a.output, filter='data')
subprocess.run(['patch', '-p1', '--fuzz=0', '--no-backup-if-mismatch', '--batch',
                '-i', str(patch)], cwd=a.output, check=True)
tree = hashlib.sha256()
for file in sorted(a.output.rglob('*')):
    if file.is_dir():
        continue
    name = file.relative_to(a.output).as_posix()
    data = str(file.readlink()).encode() if file.is_symlink() else file.read_bytes()
    tree.update(name.encode() + b'\0' + hashlib.sha256(data).digest() + b'\n')
assert tree.hexdigest() == policy['source_tree_sha256']
print('Pinned glibc 2.44 source with Ubuntu multiarch patch prepared')
