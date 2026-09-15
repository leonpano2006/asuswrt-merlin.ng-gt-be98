#!/usr/bin/env python3
"""Verify packed contents, original compatibility paths, modules and scoped overlays."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile

spec = importlib.util.spec_from_file_location('migration', Path(__file__).with_name('migrate-rootfs.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def inventory(root):
    result = {}
    for path in m.entries(root):
        s = path.lstat()
        row = {'mode': stat.S_IMODE(s.st_mode)}
        if stat.S_ISLNK(s.st_mode):
            target = m.resolve(root, path.relative_to(root))
            row.update(kind='link', target=os.readlink(path), resolved=target.relative_to(root).as_posix())
            if target.is_file():
                row['resolved_sha256'] = m.sha(target)
        elif stat.S_ISREG(s.st_mode):
            row.update(kind='file', sha256=m.sha(path), bytes=s.st_size)
        elif stat.S_ISDIR(s.st_mode):
            row['kind'] = 'directory'
        else:
            row.update(kind='special', rdev=s.st_rdev, filetype=stat.S_IFMT(s.st_mode))
        result[path.relative_to(root).as_posix()] = row
    return result

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True, help='queued NVRAM-fixed baseline rootfs')
p.add_argument('--source-inventory', type=Path, required=True)
p.add_argument('--rootfs', type=Path, required=True)
p.add_argument('--integrated-rootfs', type=Path, required=True)
p.add_argument('--squashfs', type=Path, required=True)
p.add_argument('--library-report', type=Path, required=True)
p.add_argument('--report', type=Path, required=True)
a = p.parse_args()
source, root = a.source.resolve(strict=True), a.rootfs.resolve(strict=True)
assert not a.report.exists()
assert inventory(source) == json.loads(a.source_inventory.read_text()), 'baseline changed'
expected = inventory(root)
assert inventory(a.integrated_rootfs) == expected, 'integrated recipe differs from tested rootfs'
with tempfile.TemporaryDirectory(prefix='armel-verify-') as temp:
    extracted = Path(temp)/'rootfs'
    subprocess.run(['unsquashfs', '-processors', '4', '-no-progress', '-d', str(extracted), str(a.squashfs)],
                   check=True, stdout=subprocess.DEVNULL)
    assert inventory(extracted) == expected, 'SquashFS contents differ from staged rootfs'
overlay = {row['target']: row['output_sha256'] for row in json.loads(a.library_report.read_text())}
preserved = rebuilt_aliases = modules = 0
for old in m.entries(source):
    name = old.relative_to(source).as_posix()
    previous, current = m.resolve(source, name), m.resolve(root, name)
    if not previous.is_file() or previous.relative_to(source).as_posix() == 'rom/etc/ld.so.conf':
        continue
    assert current.is_file(), name
    new_name = current.relative_to(root).as_posix()
    if new_name in overlay:
        assert m.sha(current) == overlay[new_name]
        rebuilt_aliases += 1
    else:
        assert m.sha(previous) == m.sha(current), name
        preserved += 1
    assert stat.S_IMODE(previous.stat().st_mode) == stat.S_IMODE(current.stat().st_mode), name
    if name.endswith('.ko'):
        modules += 1
assert not any(m.abi(path) == 'armel' for path in (root/'usr/lib').iterdir())
assert m.sha(root/'usr/lib/arm-linux-gnueabi/libnvram.so') == '45066c6af9c9a8b843057b6d7bc341a49e3b90fae3d381d06a5f99bb54517b00'
report = {'source_unchanged': True, 'integrated_recipe_identical': True, 'squashfs_matches_staging': True,
          'original_file_paths_preserved_bytewise': preserved,
          'original_paths_to_four_rebuilt_libraries': rebuilt_aliases,
          'unchanged_modules': modules, 'flat_armel_elf_files_remaining': 0,
          'webui_fix_preserved': True, 'squashfs_bytes': a.squashfs.stat().st_size,
          'squashfs_sha256': m.sha(a.squashfs),
          'inventory_sha256': hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest(),
          'firmware_packaged': False, 'hardware_boot_tested': False, 'router_modified': False}
a.report.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
