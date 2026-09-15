#!/usr/bin/env python3
"""Stage rebuilt glibc as a matched loader/libc set; preserve public ABI."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from common import sha, elf_info

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--baseline-rootfs', type=Path, required=True)
p.add_argument('--builds', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
assert not a.output.exists()
rows = []
for abi, triplet, loader in [('aarch64', 'aarch64-linux-gnu', 'ld-linux-aarch64.so.1'),
                             ('armel', 'arm-linux-gnueabi', 'ld-linux.so.3'),
                             ('armhf', 'arm-linux-gnueabihf', 'ld-linux-armhf.so.3')]:
    build = a.builds / abi
    cfg = json.loads((build / 'configuration.json').read_text())
    assert all(row['returncode'] == 0 for row in json.loads((build / 'result.json').read_text()))
    stage = build / 'stage'
    files = [(f, Path('usr/lib') / triplet / f.name)
             for f in sorted((stage / 'lib' / triplet).glob('*.so*'))
             if f.is_file() and not f.is_symlink()]
    files.append((stage / 'lib' / loader, Path('usr/lib') / triplet / loader))
    if abi == 'aarch64':
        files.append((stage / 'sbin/ldconfig', Path('usr/sbin/ldconfig')))
    strip = 'strip' if abi == 'aarch64' else str(Path(shlex.split(cfg['cc'])[0]).parent / (triplet + '-strip'))
    env = dict(os.environ)
    if cfg.get('host_library_dir'):
        env['LD_LIBRARY_PATH'] = cfg['host_library_dir']
    for src, relative in files:
        before = a.baseline_rootfs / relative
        if not before.exists():
            # Preserve the deployed runtime component set. Full staged installs
            # retain SDK headers, archives and gconv modules outside firmware.
            continue
        assert before.is_file() and not before.is_symlink(), relative
        old, new = elf_info(before), elf_info(src)
        for key in ('class', 'machine', 'float_abi_flags', 'soname'):
            assert old[key] == new[key], (relative, key)
        missing = {k: v for k, v in old['exports'].items() if new['exports'].get(k) != v}
        assert not missing, (relative, missing)
        target = a.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        subprocess.run([strip, '--strip-unneeded', str(target)], env=env, check=True)
        rows.append({'abi': abi, 'path': str(relative), 'input_sha256': sha(before),
                     'output_sha256': sha(target), 'bytes': target.stat().st_size,
                     'public_exports_preserved': len(old['exports']),
                     'new_public_exports': sorted(set(new['exports']) - set(old['exports'])),
                     'needed': new['needed']})
(a.output.parent / 'runtime-manifest.json').write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps({'runtime_files': len(rows), 'public_ABI_preserved': True}, indent=2))
