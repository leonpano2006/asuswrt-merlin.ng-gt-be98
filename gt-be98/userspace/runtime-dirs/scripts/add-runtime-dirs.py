#!/usr/bin/env python3
"""Add /run compatibility and empty /media, /srv to an offline ASUS image."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess


def inventory(root):
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            p = Path(directory) / name
            st = p.lstat()
            row = {'mode': st.st_mode}
            if stat.S_ISLNK(st.st_mode):
                row['link'] = os.readlink(p)
            elif stat.S_ISREG(st.st_mode):
                row['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            elif not stat.S_ISDIR(st.st_mode):
                row['rdev'] = st.st_rdev
            result[p.relative_to(root).as_posix()] = row
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    source, output = a.source.resolve(strict=True), a.output.absolute()
    if source == Path('/') or not (source / 'rom/etc').is_dir():
        p.error('Source must be an offline ASUS rootfs')
    if output.exists() or output.is_symlink() or source in output.parents or output in source.parents:
        p.error('Use a new output outside the source tree')
    for name in ('bin', 'sbin', 'lib'):
        if not (source / name).is_symlink() or os.readlink(source / name) != 'usr/' + name:
            p.error('Apply merged-/usr first')
    for name in ('run', 'media', 'srv'):
        if os.path.lexists(source / name):
            p.error('Unexpected existing path: ' + name)
    before = inventory(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['cp', '-a', '--reflink=auto', str(source), str(output)], check=True)
    (output / 'run').symlink_to('var/run')
    for name in ('media', 'srv'):
        (output / name).mkdir(mode=0o755)
        (output / name).chmod(0o755)
    after = inventory(output)
    assert set(after) - set(before) == {'run', 'media', 'srv'}
    assert all(after[name] == row for name, row in before.items())
    assert inventory(source) == before
    result = {'added': {name: after[name] for name in ('run', 'media', 'srv')},
              'preserved_entries': len(before), 'existing_entries_unchanged': True,
              'source_unchanged': True, 'init_changed': False,
              'runtime_backend': 'Existing ASUS /var tmpfs, /var/run root:root 0755',
              'var_lock_changed': False, 'router_modified': False}
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
