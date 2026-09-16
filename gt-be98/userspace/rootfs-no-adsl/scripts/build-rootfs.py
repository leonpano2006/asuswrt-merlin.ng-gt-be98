#!/usr/bin/env python3
"""Remove one hash-pinned GT-BE98 payload from isolated staging, then verify the image."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from common import inventory, inventory_sha

r = Path(__file__).resolve().parents[1]
w = r.parent
source = w / 'a53-runtimes-20260916/build/unpacked-rootfs'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
original = w / 'a53-runtimes-20260916/build/rootfs.squashfs'
assert sha(original) == '68888e499d0095374266c8f2adf0be296c5370e893c81c548e7a36c1030e9216'
audit = json.loads((r / 'evidence/adsl-audit.json').read_text())
assert audit['model'] == 'GT-BE98'
target = 'rom/etc/adsl1/adsl_phy.bin'
assert audit['target'] == target
record = json.loads((r / 'evidence/source-inventory.json').read_text())
before = inventory(source)
assert before == {p: {k: v for k, v in row.items() if k != 'mtime_ns'} for p, row in record.items()}
assert sha(source / target) == audit['target_sha256']
staging = r / 'build/staged-rootfs'
assert not staging.exists()
subprocess.run(['cp', '-a', '--reflink=auto', str(source), str(staging)], check=True)
assert inventory(staging) == before
parent = (staging / target).parent
parent_stat = parent.stat()
(staging / target).unlink()
os.utime(parent, ns=(parent_stat.st_atime_ns, parent_stat.st_mtime_ns))
expected = dict(before)
removed = expected.pop(target)
assert inventory(staging) == expected
candidate_record = {p: v for p, v in record.items() if p != target}
(r / 'evidence/candidate-inventory.json').write_text(json.dumps(candidate_record, indent=2, sort_keys=True) + '\n')
image = r / 'build/zstd22-1m-tailends.squashfs'
assert not image.exists()
command = ['nice', '-n', '10', 'mksquashfs', str(staging), str(image), '-noappend',
           '-all-root', '-comp', 'zstd', '-Xcompression-level', '22', '-b', '1048576',
           '-processors', '4', '-mem', '512M', '-mkfs-time', '1789556948',
           '-no-progress', '-exit-on-error', '-tailends']
started = time.monotonic()
with (r / 'evidence/pack.log').open('w') as log:
    subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
elapsed = time.monotonic() - started
output = r / 'build/unpacked-rootfs'
assert not output.exists()
with (r / 'evidence/unpack.log').open('w') as log:
    subprocess.run(['unsquashfs', '-no-progress', '-processors', '4', '-d', str(output), str(image)],
                   stdout=log, stderr=subprocess.STDOUT, check=True)
found = inventory(output)
assert found == expected, 'Unexpected file/content/mode/link difference'
assert all(int((source / p).lstat().st_mtime) == int((output / p).lstat().st_mtime)
           for p in ['.'] + list(found)), 'Unexpected mtime difference'
assert inventory(source) == before, 'Original source changed'
result = {'removed': {target: removed}, 'added_paths': [], 'changed_remaining_paths': [],
          'remaining_inventory_sha256': inventory_sha(found), 'all_paths': len(found),
          'regular_files': sum(v['kind'] == 'file' for v in found.values()),
          'module_files_unchanged': sum(p.endswith('.ko') for p in found),
          'all_remaining_contents_modes_links_match': True, 'all_remaining_timestamps_match': True,
          'original_source_unchanged': True}
(r / 'evidence/content-verification.json').write_text(json.dumps(result, indent=2) + '\n')
selected = {'label': 'zstd22-1m-tailends', 'bytes': image.stat().st_size, 'sha256': sha(image),
            'seconds': round(elapsed, 3), 'command': command,
            'rootfs_reserved_ubi_blocks': (image.stat().st_size + 1048576 + 126975) // 126976,
            'saved_vs_installed_bytes': original.stat().st_size - image.stat().st_size,
            'saved_vs_compression_only_bytes': 75309056 - image.stat().st_size}
(r / 'evidence/compression-results.json').write_text(json.dumps([selected], indent=2) + '\n')
print(json.dumps({'content_verification': result, 'compression': selected}, indent=2))
