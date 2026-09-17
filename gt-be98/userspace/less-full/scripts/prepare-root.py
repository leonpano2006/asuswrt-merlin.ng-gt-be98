#!/usr/bin/env python3
"""Overlay the full less package; unlink applet aliases before installing."""
from pathlib import Path
import json
import shutil
import subprocess
from common import inventory

r = Path(__file__).resolve().parents[1]
parent = r.parent / 'systemd-upgrade-20260917/build/production-rootfs'
root = r / 'build/production-rootfs'
assert not root.exists()
subprocess.run(['cp', '-a', '--reflink=auto', str(parent), str(root)], check=True)
before = inventory(root)
for source in (r / 'stage').rglob('*'):
    if not source.is_file():
        continue
    dest = root / source.relative_to(r / 'stage')
    dest.parent.mkdir(parents=True, exist_ok=True)
    # In particular, never follow less -> ../../bin/busybox during install.
    if dest.is_symlink():
        dest.unlink()
    shutil.copy2(source, dest)
after = inventory(root)
changes = {n: after.get(n) for n in before.keys() | after.keys()
           if before.get(n) != after.get(n)}
allowed = {f.relative_to(r / 'stage').as_posix() for f in (r / 'stage').rglob('*')}
assert changes.keys() <= allowed
assert before['usr/bin/busybox'] == after['usr/bin/busybox']
(r / 'evidence/rootfs-changes.json').write_text(json.dumps({
    'parent': 'systemd-upgrade-20260917', 'changed': changes,
    'all_other_paths_identical': True}, indent=2) + '\n')
print('ONLY_LESS_PACKAGE_CHANGED', len(changes))
