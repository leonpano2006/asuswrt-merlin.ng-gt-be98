#!/usr/bin/env python3
"""Build a read-only SquashFS guest test using external, pinned checkpoint inputs."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import stat
from elftools.elf.elffile import ELFFile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--busybox', type=Path, required=True)
p.add_argument('--probes', type=Path, required=True)
p.add_argument('--squashfs', type=Path, required=True)
p.add_argument('--rootfs', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
r = Path(__file__).resolve().parents[1]
executables = []
for path in sorted(a.rootfs.rglob('*')):
    if path.is_symlink() or not path.is_file():
        continue
    with path.open('rb') as f:
        if f.read(4) != b'\x7fELF':
            continue
        f.seek(0)
        elf = ELFFile(f)
        for segment in elf.iter_segments():
            if segment.header.p_type == 'PT_INTERP':
                interp = segment.get_interp_name()
                name = '/' + path.relative_to(a.rootfs).as_posix()
                executables.append((interp, name))
                break
entries = {d: (stat.S_IFDIR | 0o755, b'', 0, 0) for d in ('bin', 'dev', 'proc', 'sys', 'tmp', 'newroot')}
files = {
    'bin/busybox': a.busybox,
    'rootfs.squashfs': a.squashfs,
    'identity-probe': a.probes / 'identity-probe',
    'guardcheck': a.probes / 'guardcheck',
    'provider.so': a.probes / 'bootguard-provider.so',
    'userspace-smoke.sh': r / 'scripts/userspace-smoke.sh',
    'init': r / 'scripts/guest-init.sh',
}
for abi in ('aarch64', 'armel', 'armhf'):
    files['abi-probe-' + abi] = a.probes / ('abi-probe-' + abi)
for name, path in files.items():
    entries[name] = (stat.S_IFREG | 0o755, path.read_bytes(), 0, 0)
entries['dynamic-executables.txt'] = (stat.S_IFREG | 0o444, ''.join(ld + ' ' + n + '\n' for ld, n in executables).encode(), 0, 0)
entries.update({'dev/console': (stat.S_IFCHR | 0o600, b'', 5, 1),
                'dev/null': (stat.S_IFCHR | 0o666, b'', 1, 3),
                'dev/loop0': (stat.S_IFBLK | 0o600, b'', 7, 0),
                'TRAILER!!!': (0, b'', 0, 0)})
out = bytearray()
for ino, (name, (mode, data, major, minor)) in enumerate(entries.items(), 1):
    name = name.encode() + b'\0'
    fields = [ino, mode, 0, 0, 2 if stat.S_ISDIR(mode) else 1, 0, len(data), 0, 0, major, minor, len(name), 0]
    out.extend(b'070701' + ''.join(f'{v:08x}' for v in fields).encode() + name)
    out.extend(b'\0' * (-len(out) % 4))
    out.extend(data)
    out.extend(b'\0' * (-len(out) % 4))
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_bytes(gzip.compress(out, compresslevel=1, mtime=0))
(r / 'evidence').mkdir(parents=True, exist_ok=True)
(r / 'evidence/dynamic-executables.json').write_text(json.dumps(executables, indent=2) + '\n')
print(json.dumps({'executables': len(executables), 'bytes': a.output.stat().st_size,
                  'sha256': hashlib.sha256(a.output.read_bytes()).hexdigest()}, indent=2))
