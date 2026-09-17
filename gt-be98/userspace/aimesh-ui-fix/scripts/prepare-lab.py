#!/usr/bin/env python3
"""Overlay fixes on the prior offline rehearsal, preserving all other paths."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil
import subprocess
import sys

r = Path(__file__).resolve().parents[1]
w = r.parent
platform = w / 'systemd-rc-platform-20260917'
sys.path.insert(0, str(platform / 'scripts'))
from common import inventory, sha

base = platform / 'build/platform-v7/rootfs'
root = r / 'build/lab-rootfs'
assert not root.exists()
subprocess.run(['cp', '-a', '--reflink=auto', str(base), str(root)], check=True)
changes = {
    'usr/sbin/httpd': r / 'build/httpd/httpd.stripped',
    'usr/sbin/rc': r / 'build/rc/rc.stripped',
    'usr/lib/arm-linux-gnueabi/libshared.so': w / 'httpd-dashboard-fix-20260917/build/libshared.stripped.so',
    'www/aimesh/aimesh_topology.html': r / 'build/aimesh_topology.html',
}
for name, source in changes.items():
    target = root / name
    assert target.is_file() and not target.is_symlink(), name
    shutil.copyfile(source, target)
before, after = inventory(base), inventory(root)
assert before.keys() == after.keys()
assert {name for name in before if before[name] != after[name]} == set(changes)
squash = r / 'build/lab.squashfs'
with (r / 'evidence/lab-pack.log').open('w') as log:
    subprocess.run(['mksquashfs', str(root), str(squash), '-noappend', '-all-root',
                    '-comp', 'zstd', '-Xcompression-level', '3', '-b', '1048576',
                    '-processors', '4', '-mem', '512M', '-no-progress', '-exit-on-error'],
                   stdout=log, stderr=subprocess.STDOUT, check=True)
old = gzip.decompress((platform / 'build/platform-v7/guest.cpio.gz').read_bytes())
data = bytearray()
pos = 0
replaced = 0
while pos + 110 <= len(old):
    assert old[pos:pos + 6] == b'070701'
    fields = [int(old[pos + 6 + 8*i:pos + 14 + 8*i], 16) for i in range(13)]
    size, namesize = fields[6], fields[11]
    name = old[pos + 110:pos + 110 + namesize]
    start = (pos + 110 + namesize + 3) & ~3
    content = old[start:start + size]
    pos = (start + size + 3) & ~3
    if name == b'rootfs.squashfs\0':
        content = squash.read_bytes()
        fields[6] = len(content)
        replaced += 1
    data += b'070701' + ''.join(f'{x:08x}' for x in fields).encode() + name
    data += b'\0' * (-len(data) % 4)
    data += content
    data += b'\0' * (-len(data) % 4)
    if name == b'TRAILER!!!\0':
        break
assert replaced == 1
guest = r / 'build/guest.cpio.gz'
guest.write_bytes(gzip.compress(data, compresslevel=1, mtime=0))
report = {'purpose': 'offline rehearsal only, not a firmware image',
          'only_changed_paths': {name: sha(root / name) for name in changes},
          'guest_sha256': sha(guest)}
(r / 'evidence/lab-overlay.json').write_text(json.dumps(report, indent=2) + '\n')
shutil.copyfile(platform / 'scripts/run-qemu.py', r / 'scripts/run-qemu.py')
print(json.dumps(report, indent=2))
