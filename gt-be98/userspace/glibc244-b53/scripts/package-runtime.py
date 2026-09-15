#!/usr/bin/env python3
"""Package stripped copies using the existing GT-BE98 loader/ABI layout."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tarfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--work', type=Path, required=True)
args = p.parse_args()
r = args.work.resolve()
(r / 'evidence').mkdir(parents=True, exist_ok=True)
root = r / 'packages/runtime'
root.mkdir(parents=True, exist_ok=False)
records = []
for abi in ['aarch64', 'armel', 'armhf']:
    cfg = json.loads((r / 'builds' / abi / 'configuration.json').read_text())
    stage = r / 'builds' / abi / 'stage'
    lib = Path(cfg['configuration']['slibdir'].lstrip('/'))
    devlib = Path(cfg['configuration']['libdir'].lstrip('/'))
    dest = root / lib
    dest.mkdir(parents=True, exist_ok=True)
    strip = 'strip' if abi == 'aarch64' else str(r / 'toolchains/arm32-ubuntu/usr/bin' / (cfg['configuration']['host'] + '-strip'))
    environment = dict(os.environ)
    if cfg.get('host_library_dir'):
        environment['LD_LIBRARY_PATH'] = cfg['host_library_dir']
    files = []
    for file in (stage / lib).glob('*.so*'):
        target = dest / file.name
        shutil.copy2(file, target, follow_symlinks=False)
        files.append(target)
    if abi == 'aarch64':
        loader = dest / 'ld-linux-aarch64.so.1'
        shutil.copy2(stage / 'lib/ld-linux-aarch64.so.1', loader)
        files.append(loader)
        (root / 'lib/ld-linux-aarch64.so.1').symlink_to('aarch64-linux-gnu/ld-linux-aarch64.so.1')
    elif abi == 'armhf':
        (root / 'lib/ld-linux-armhf.so.3').symlink_to('arm-linux-gnueabihf/ld-linux-armhf.so.3')
    gconv = root / devlib / 'gconv'
    shutil.copytree(stage / devlib / 'gconv', gconv, symlinks=True)
    files.extend(gconv.glob('*.so'))
    for file in files:
        if file.is_symlink():
            continue
        subprocess.run([strip, '--strip-unneeded', str(file)], env=environment, check=True)
        records.append({'abi': abi, 'path': str(file.relative_to(root)),
                        'bytes': file.stat().st_size,
                        'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
(r / 'evidence/runtime-manifest.json').write_text(json.dumps(records, indent=2) + '\n')
archive = r / 'packages/glibc-2.44-b53-runtime.tar.gz'
with tarfile.open(archive, 'w:gz') as tar:
    def owner(info):
        info.uid = info.gid = 0
        info.uname = info.gname = 'root'
        return info
    tar.add(root, arcname='.', filter=owner)
print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size,
                  'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}, indent=2))
zstd_archive = archive.with_suffix('').with_suffix('.tar.zst')
# Reuse the exact tested tar payload, with zstd level 22 for preservation.
with gzip.open(archive, 'rb') as stream:
    subprocess.run(['zstd', '--ultra', '-22', '-T4', '-q', '-o', str(zstd_archive)],
                   input=stream.read(), check=True)
print(json.dumps({'archive': str(zstd_archive), 'bytes': zstd_archive.stat().st_size,
                  'sha256': hashlib.sha256(zstd_archive.read_bytes()).hexdigest()}, indent=2))
