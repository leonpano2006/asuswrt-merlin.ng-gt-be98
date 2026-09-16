#!/usr/bin/env python3
"""Reuse the verified runtime guest, adding a read/hash of every rootfs file."""
import gzip
import hashlib
import json
from pathlib import Path
import stat

r = Path(__file__).resolve().parents[1]
w = r.parent
old = w / 'a53-runtimes-20260916/build/guest.cpio.gz'
candidate = r / 'build/zstd22-1m-tailends.squashfs'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(old) == '4a4bebee33080471d2a204269095d7869c7c0169a4fe9d76dae8117b9d337dae'
results = json.loads((r / 'evidence/compression-results.json').read_text())
selected = next(x for x in results if x['label'] == 'zstd22-1m-tailends')
assert sha(candidate) == selected['sha256']
raw = gzip.decompress(old.read_bytes())
entries = {}
pos = 0
while pos < len(raw):
    assert raw[pos:pos + 6] == b'070701'
    fields = [int(raw[pos + 6 + 8 * i:pos + 14 + 8 * i], 16) for i in range(13)]
    size, name_size = fields[6], fields[11]
    name = raw[pos + 110:pos + 110 + name_size - 1].decode()
    start = (pos + 110 + name_size + 3) & ~3
    if name == 'TRAILER!!!':
        break
    entries[name] = (fields[1], raw[start:start + size], fields[9], fields[10])
    pos = (start + size + 3) & ~3

manifest = json.loads((r / 'evidence/candidate-inventory.json').read_text())
checksums = []
for name, info in sorted(manifest.items()):
    if info['kind'] == 'file':
        assert '\n' not in name and '\\' not in name
        checksums.append(info['sha256'] + '  /newroot/' + name + '\n')
assert len(checksums) == 3482
entries['rootfs.squashfs'] = (stat.S_IFREG | 0o444, candidate.read_bytes(), 0, 0)
entries['rootfs-files.sha256'] = (stat.S_IFREG | 0o444, ''.join(checksums).encode(), 0, 0)
mode, init, major, minor = entries['init']
marker = b'mount -t squashfs -o ro /dev/loop0 /newroot\n'
assert init.count(marker) == 1
verify = b'''test ! -e /newroot/rom/etc/adsl1/adsl_phy.bin || exit 1
echo LAB_ADSL_PHY_ABSENT_PASS
echo LAB_SQUASHFS_ALL_FILES_BEGIN
if ! sha256sum -c /rootfs-files.sha256 > /tmp/all-files-hashes.txt 2>&1; then
    grep -v ': OK$' /tmp/all-files-hashes.txt
    exit 1
fi
echo LAB_SQUASHFS_ALL_FILES_PASS_count_3482
'''
entries['init'] = (mode, init.replace(marker, marker + verify), major, minor)
entries['TRAILER!!!'] = (0, b'', 0, 0)
output = bytearray()
for ino, (name, (mode, data, major, minor)) in enumerate(entries.items(), 1):
    name = name.encode() + b'\0'
    fields = [ino, mode, 0, 0, 2 if stat.S_ISDIR(mode) else 1, 0, len(data), 0, 0,
              major, minor, len(name), 0]
    output += b'070701' + ''.join(f'{value:08x}' for value in fields).encode() + name
    output += b'\0' * (-len(output) % 4)
    output += data
    output += b'\0' * (-len(output) % 4)
image = r / 'build/guest.cpio.gz'
image.write_bytes(gzip.compress(output, compresslevel=1, mtime=0))
(r / 'evidence/qemu-inputs.json').write_text(json.dumps({
    'original_guest_sha256': sha(old), 'candidate_sha256': sha(candidate),
    'guest_sha256': sha(image), 'regular_files_hashed_in_kernel': len(checksums),
    'prior_runtime_tests_preserved': True, 'router_modified': False,
}, indent=2) + '\n')
print('Prepared QEMU guest: ' + str(image.stat().st_size) + ' bytes')
