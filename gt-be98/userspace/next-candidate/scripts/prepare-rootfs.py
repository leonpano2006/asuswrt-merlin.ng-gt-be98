#!/usr/bin/env python3
"""Stage the queued fix into a new rootfs before next-candidate packaging."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def inventory(root):
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(directory) / name
            s = path.lstat()
            row = {'mode': s.st_mode}
            if stat.S_ISLNK(s.st_mode):
                row['link'] = os.readlink(path)
            elif stat.S_ISREG(s.st_mode):
                row.update(sha256=sha(path), bytes=s.st_size)
            elif not stat.S_ISDIR(s.st_mode):
                row['rdev'] = s.st_rdev
            result[path.relative_to(root).as_posix()] = row
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-squashfs', type=Path, required=True)
    parser.add_argument('--patch-script', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads((Path(__file__).resolve().parent.parent/'candidate.json').read_text())
    change, = config['required_changes']
    output = args.output.resolve()
    if output.exists() or args.output.is_symlink():
        parser.error('Output must be a new, offline rootfs directory')
    if args.base_squashfs.stat().st_size != config['base_rootfs_bytes'] or sha(args.base_squashfs) != config['base_rootfs_sha256']:
        parser.error('Unrecognized baseline SquashFS')
    if sha(args.patch_script) != change['generator_sha256']:
        parser.error('Unrecognized patch generator')
    if args.report.exists():
        parser.error('Report must not already exist')
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['unsquashfs', '-processors', '4', '-no-progress', '-d', str(output),
                    str(args.base_squashfs)], check=True)
    for name in ('bin', 'sbin', 'lib'):
        assert (output/name).is_symlink() and os.readlink(output/name) == 'usr/'+name
    assert os.readlink(output/'run') == 'var/run'
    target = output/change['target']
    assert not target.is_symlink() and target.resolve().is_relative_to(output)
    before = inventory(output)
    assert sha(target) == change['input_sha256']
    spec = importlib.util.spec_from_file_location('candidate_patch', args.patch_script)
    patcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patcher)
    data, _ = patcher.patch(target.read_bytes())
    assert hashlib.sha256(data).hexdigest() == change['output_sha256']
    assert len(data) == change['bytes']
    target.write_bytes(data)
    assert stat.S_IMODE(target.stat().st_mode) == int(change['mode'], 8)
    after = inventory(output)
    assert before.keys() == after.keys()
    changed = [name for name in before if before[name] != after[name]]
    assert changed == [change['target']]
    assert before[change['target']]['mode'] == after[change['target']]['mode']
    modules = [name for name in before if name.endswith('.ko')]
    assert all(before[name] == after[name] for name in modules)
    assert sha(args.base_squashfs) == config['base_rootfs_sha256']
    report = {'candidate': config['candidate'], 'status': 'rootfs-prepared-for-next-packaging',
              'base_rootfs_sha256': config['base_rootfs_sha256'], 'changed_paths': changed,
              'patched_library_sha256': sha(target), 'preserved_entries': len(before)-1,
              'unchanged_module_files': len(modules), 'source_unchanged': True,
              'firmware_packaged': False, 'router_modified': False,
              'firmware_commit_performed': False}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
