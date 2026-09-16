#!/usr/bin/env python3
"""Stage pinned extracted GCC 15 libraries and the existing GCC 16.2 library."""
import argparse
import json
from pathlib import Path
import shutil
from common import sha

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--baseline', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
policy = json.loads((root / 'configs/runtime-policy.json').read_text())
manifest = root / 'packages/runtime-manifest.json'
assert sha(manifest) == policy['runtime_manifest_sha256']
rows = json.loads(manifest.read_text())
assert not a.output.exists() and not a.output.is_symlink()
assert a.output.resolve() != Path('/')
sources = []
for row in rows:
    if row['action'] == 'retain-verified':
        source = a.baseline / row['path']
    else:
        triplet = Path(row['path']).parent.name
        source = root / 'extracted' / row['abi'] / 'usr' / triplet / 'lib/libgcc_s.so.1'
        archive = root / 'downloads' / Path(row['package']['filename']).name
        assert sha(archive) == row['package']['sha256']
    assert sha(source) == row['output_sha256'], row['abi']
    assert source.stat().st_size == row['bytes']
    sources.append((row, source))
for row, source in sources:
    target = a.output / row['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    target.chmod(row['mode'])
print('Staged three pinned libgcc runtimes:', a.output)
