#!/usr/bin/env python3
"""Minimal network-isolated #36/A53 VM for real ARM32/ARM64 TLS interoperability."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
from elftools.elf.elffile import ELFFile

r = Path(__file__).resolve().parents[1]
w = r.parent
parent = w / 'systemd-rc-next-20260917/build/production-rootfs'
out = r / 'build/crypto-qemu-v2'
out.mkdir(exist_ok=False)
root = out / 'rootfs'
shutil.copytree(r / 'overlay', root)
for d in ['dev', 'proc', 'sys', 'tmp', 'run', 'etc', 'var/lib/systemd', 'usr/bin', 'usr/sbin', 'probe']:
    (root / d).mkdir(parents=True, exist_ok=True)
(root / 'bin').symlink_to('usr/bin')
(root / 'lib').symlink_to('usr/lib')
machine_id = '11223344556677889900aabbccddeeff00'[:32]
assert len(bytes.fromhex(machine_id)) == 16
(root / 'etc/machine-id').write_text(machine_id + '\n')
# Retain the existing ARM32 executable, loader and libraries byte for byte.
for name in ['usr/sbin/openssl', 'usr/lib/arm-linux-gnueabi/libssl.so.3',
             'usr/lib/arm-linux-gnueabi/libcrypto.so.3']:
    p = root / name; p.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(parent / name, p)
for abi, ld in [('aarch64-linux-gnu', 'ld-linux-aarch64.so.1'), ('arm-linux-gnueabi', 'ld-linux.so.3')]:
    for name in [ld, 'libc.so.6', 'libm.so.6']:
        p = root / 'usr/lib' / abi / name; p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(parent / 'usr/lib' / abi / name, p)
    (root / 'usr/lib' / ld).symlink_to(abi + '/' + ld)
for src, dst in [('systemd-creds', 'systemd-creds'), ('src/shared/libsystemd-shared-257.so', 'libsystemd-shared-257.so')]:
    p = root / 'probe' / dst
    shutil.copy2(r / 'build/systemd-openssl4' / src, p)
    subprocess.run(['aarch64-linux-gnu-strip', '--strip-unneeded', str(p)], check=True)
# Copy the transitive runtime closure only from the recorded firmware root.
pending = list(root.rglob('*'))
while pending:
    p = pending.pop()
    if p.is_symlink() or not p.is_file(): continue
    with p.open('rb') as f:
        if f.read(4) != b'\x7fELF': continue
        f.seek(0); e = ELFFile(f); d = e.get_section_by_name('.dynamic')
        abi = 'aarch64-linux-gnu' if e.elfclass == 64 else 'arm-linux-gnueabi'
        for tag in d.iter_tags() if d else []:
            if tag.entry.d_tag == 'DT_NEEDED':
                dest = root / 'usr/lib' / abi / tag.needed
                if not dest.exists() and not (root / 'probe' / tag.needed).exists():
                    source = parent / 'usr/lib' / abi / tag.needed
                    assert source.is_file(), (p, tag.needed)
                    shutil.copy2(source, dest)
                    pending.append(dest)
raw = gzip.decompress((w / 'systemd-lab-20260916/build/guard-service/guest.cpio.gz').read_bytes())
pos = 0
while pos < len(raw):
    assert raw[pos:pos+6] == b'070701'
    fields = [int(raw[pos+6+8*i:pos+14+8*i], 16) for i in range(13)]
    size, namesize = fields[6], fields[11]
    name = raw[pos+110:pos+110+namesize-1].decode(); start = (pos+110+namesize+3) & ~3
    if name == 'bin/busybox':
        (root / 'usr/bin/busybox').write_bytes(raw[start:start+size]); break
    pos = (start+size+3) & ~3
else: raise RuntimeError('parent fixture lacks busybox')
(root / 'usr/bin/busybox').chmod(0o755)
for name in ['sh', 'mount', 'mkdir', 'poweroff', 'uname', 'grep', 'cmp', 'wc', 'ip', 'sleep']:
    (root / 'usr/bin' / name).symlink_to('busybox')
shutil.copy2(r / 'tests/openssl4-qemu-init.sh', root / 'init'); (root / 'init').chmod(0o755)
entries = {}
for path in sorted(root.rglob('*')):
    st = path.lstat(); name = path.relative_to(root).as_posix()
    data = str(path.readlink()).encode() if path.is_symlink() else path.read_bytes() if stat.S_ISREG(st.st_mode) else b''
    entries[name] = (st.st_mode, data, 0, 0)
entries.update({'dev/console': (stat.S_IFCHR | 0o600, b'', 5, 1),
                'dev/null': (stat.S_IFCHR | 0o666, b'', 1, 3),
                'dev/random': (stat.S_IFCHR | 0o666, b'', 1, 8),
                'dev/urandom': (stat.S_IFCHR | 0o666, b'', 1, 9),
                'TRAILER!!!': (0, b'', 0, 0)})
data = bytearray()
for ino, (name, (mode, content, major, minor)) in enumerate(entries.items(), 1):
    encoded = name.encode() + b'\0'
    fields = [ino, mode, 0, 0, 2 if stat.S_ISDIR(mode) else 1, 0, len(content), 0, 0, major, minor, len(encoded), 0]
    data += b'070701' + ''.join(f'{x:08x}' for x in fields).encode() + encoded
    data += b'\0' * (-len(data) % 4); data += content; data += b'\0' * (-len(data) % 4)
guest = out / 'guest.cpio.gz'; guest.write_bytes(gzip.compress(data, compresslevel=1, mtime=0))
record = {'guest_sha256': hashlib.sha256(guest.read_bytes()).hexdigest(), 'guest_bytes': guest.stat().st_size,
          'purpose': 'OpenSSL 4 and systemd-creds compatibility, not a full PID 1/firmware test',
          'source_overlay_manifest': json.loads((r / 'evidence/openssl4-overlay.json').read_text()),
          'host_disks': False, 'external_network': False}
(out / 'manifest.json').write_text(json.dumps(record, indent=2) + '\n')
runner = (w / 'systemd-rc-next-20260917/scripts/run-qemu.py').read_text().replace(
    'LAB_SYSTEMD_ALL_PASS', 'LAB_OPENSSL4_ALL_PASS').replace('LAB_SYSTEMD_CHECK_FAILURE', 'LAB_OPENSSL4_CHECK_FAILURE')
(r / 'scripts/run-crypto-qemu.py').write_text(runner)
print('CRYPTO_QEMU_READY', guest.stat().st_size)
