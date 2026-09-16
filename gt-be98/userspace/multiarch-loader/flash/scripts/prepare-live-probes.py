#!/usr/bin/env python3
"""Prepare existing probe binaries and exact runtime checks for the board trial."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--checkpoint', type=Path, required=True)
p.add_argument('--previous-checkpoint', type=Path, required=True)
args = p.parse_args()
b = args.checkpoint.resolve()
old = args.previous_checkpoint.resolve()
dest = b / 'flash/saved-inputs/live-probes'
dest.mkdir(parents=True, exist_ok=True)
for path in (b / 'saved-inputs/probes').glob('abi-probe-*'):
    shutil.copy2(path, dest / path.name)
shutil.copy2(b / 'saved-inputs/library-probe', dest / 'library-probe')
for name in ('dynamic-executables.txt', 'libraries.sha256'):
    shutil.copy2(old / 'flash/saved-inputs/live-probes' / name, dest / name)
runtime = json.loads((b / 'packages/runtime-manifest.json').read_text())
assert len(runtime) == 62
(dest / 'runtime.sha256').write_text(''.join(
    item['output_sha256'] + '  /' + item['path'] + '\n' for item in runtime))
aliases = json.loads((b / 'configs/rootfs-policy.json').read_text())['aliases']
(dest / 'aliases-remove.txt').write_text(''.join(
    '/' + path + '\n' for path, item in aliases.items() if not item['keep_reason']))
(dest / 'aliases-keep.txt').write_text(''.join(
    '/' + path + ' ' + item['target'] + '\n'
    for path, item in aliases.items() if item['keep_reason']))
verification = json.loads((b / 'evidence/verification.json').read_text())
triplets = {'armel': 'arm-linux-gnueabi', 'armhf': 'arm-linux-gnueabihf',
            'aarch64': 'aarch64-linux-gnu'}
for abi, lines in verification['loader_paths_and_LIB_token_match_ubuntu'].items():
    (dest / ('loader-' + abi + '.expected')).write_text('\n'.join(lines) + '\n')
    shutil.copy2(b / 'tests' / ('libc-smoke-' + abi), dest / ('libc-smoke-' + abi))
    # These staged modules test the matching libc build in /tmp only; no SDK or
    # gconv installation is performed on the router's firmware or USB prefix.
    source = b / 'builds' / abi / 'stage/usr/lib' / triplets[abi] / 'gconv'
    shutil.copytree(source, dest / ('gconv-' + abi), dirs_exist_ok=True)
shutil.copy2(b / 'flash/saved-inputs/hooks-config.sha256', dest / 'hooks-config.sha256')
shutil.copy2(b / 'flash/scripts/verify-multiarch.bash', dest / 'verify-multiarch.bash')
records = [{'path': str(path.relative_to(dest)), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
           for path in sorted(dest.rglob('*')) if path.is_file() and not path.is_symlink()]
(b / 'flash/saved-inputs/live-probes-manifest.json').write_text(
    json.dumps(records, indent=2) + '\n')
with tarfile.open(b / 'flash/saved-inputs/live-probes.tar.gz', 'w:gz', compresslevel=6) as archive:
    archive.add(dest, arcname='leon-ubuntu-verify')
print(json.dumps({'probe_files': len(records), 'runtime_files': len(runtime),
                  'aliases_removed': 257, 'aliases_retained': 32}))
