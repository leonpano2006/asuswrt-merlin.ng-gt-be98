#!/usr/bin/env python3
"""Prepare RAM-only probes for the installed A53 candidate; never install libraries."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tarfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--checkpoint', required=True, type=Path)
p.add_argument('--previous-probes', required=True, type=Path)
args = p.parse_args()
root = args.checkpoint.resolve()
flash = root / 'flash'
dest = flash / 'saved-inputs/leon-a53-flash-verify'
if dest.exists():
    raise SystemExit('Refusing to replace existing probe payload')
shutil.copytree(args.previous_probes, dest)
shutil.copytree(root / 'build/leon-a53-runtime-verify-20260916/bin', dest / 'bin')
shutil.copy2(flash / 'saved-inputs/hooks-config.sha256', dest / 'hooks-config.sha256')
base = root / 'build/integrated-rootfs'
entries = []
for triplet in ('aarch64-linux-gnu', 'arm-linux-gnueabi', 'arm-linux-gnueabihf'):
    for path in sorted((base / 'usr/lib' / triplet).iterdir()):
        if path.is_file() and not path.is_symlink():
            entries.append((str(path.relative_to(base)), hashlib.sha256(path.read_bytes()).hexdigest()))
(dest / 'installed-libraries.sha256').write_text(''.join(f'{h}  /{path}\n' for path, h in entries))
updated = []
for line in (dest / 'libraries.sha256').read_text().splitlines():
    path = line.split(None, 1)[1]
    updated.append(hashlib.sha256((base / path.lstrip('/')).read_bytes()).hexdigest() + '  ' + path)
(dest / 'libraries.sha256').write_text('\n'.join(updated) + '\n')
source = (dest / 'verify-multiarch.bash').read_text()
source = source.replace('/tmp/leon-ubuntu-verify', '/tmp/leon-a53-flash-verify')
source = source.replace('UBUNTU_MULTIARCH', 'A53_RUNTIME')
(dest / 'verify-multiarch.bash').write_text(source)
shutil.copy2(flash / 'scripts/runtime-installed.bash', dest / 'runtime-installed.bash')
records = [(str(path.relative_to(dest)), hashlib.sha256(path.read_bytes()).hexdigest())
           for path in sorted(dest.rglob('*')) if path.is_file() and path.name != 'probe-files.sha256']
(dest / 'probe-files.sha256').write_text(''.join(h + '  ' + path + '\n' for path, h in records))
with tarfile.open(flash / 'saved-inputs/live-probes.tar.gz', 'w:gz') as archive:
    archive.add(dest, arcname=dest.name)
print(f'Prepared {len(records)} probe files and {len(entries)} installed-library hashes')
