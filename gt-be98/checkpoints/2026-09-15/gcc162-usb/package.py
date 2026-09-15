#!/usr/bin/env python3
"""Prepare the staged GCC for the existing router Entware ABI."""
from pathlib import Path
import hashlib
import subprocess
import shutil

root = Path(__file__).resolve().parent
prefix = '/tmp/mnt/JFFS/gcc-16.2.0-usb'
stage = root / 'stage' / prefix.lstrip('/')
gcc = stage / 'bin/gcc'
specpath = stage / 'lib/gcc/aarch64-unknown-linux-gnu/16.2.0/specs'
if specpath.exists():
    specpath.unlink()
specs = subprocess.check_output([str(gcc), '-dumpspecs'], text=True)
old_loader = '/lib/ld-linux-aarch64'
assert old_loader in specs, 'Unexpected GCC loader specs'
specs = specs.replace(old_loader, '/opt/lib/ld-linux-aarch64')
blocks = specs.split('\n\n')
for i, block in enumerate(blocks):
    if block.startswith('*link:\n'):
        blocks[i] = block + f' -rpath {prefix}/lib64 -rpath /opt/lib'
        break
else:
    raise RuntimeError('Missing link specs')
specpath.write_text('\n\n'.join(blocks))
(stage / 'tests').mkdir(exist_ok=True)
for name in ['test.c', 'test.cpp', 'test.sh']:
    shutil.copy2(root / name, stage / 'tests' / name)
shutil.copy2(root / 'build.sh', stage / 'build-recipe.sh')
manifest = []
for path in sorted(stage.rglob('*')):
    if path.is_file() and not path.is_symlink() and path.name != 'SHA256SUMS':
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest.append(f'{digest}  {path.relative_to(stage)}')
(stage / 'SHA256SUMS').write_text('\n'.join(manifest) + '\n')
print(stage)
print(f'Hashed {len(manifest)} installed files')
