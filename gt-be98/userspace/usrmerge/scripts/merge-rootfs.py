#!/usr/bin/env python3
"""Convert a disposable GT-BE98 rootfs copy to merged-/usr, never a live root.

All conflicts must be identical, existing aliases, or explicitly hash-pinned.
Symlink resolution is relative to the supplied image, never the build host.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import stat
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(root):
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            yield Path(directory) / name


def resolve(root, path):
    """Resolve links like chroot does, including absolute and dangling links."""
    pending = list(PurePosixPath('/' + str(path).lstrip('/')).parts[1:])
    done = []
    links = 0
    while pending:
        component = pending.pop(0)
        if component in ('', '.'):
            continue
        if component == '..':
            if done:
                done.pop()
            continue
        p = root.joinpath(*done, component)
        if p.is_symlink():
            links += 1
            if links > 40:
                raise RuntimeError('symlink loop: ' + str(path))
            target = os.readlink(p)
            if target.startswith('/'):
                done = []
            pending = list(PurePosixPath(target).parts) + pending
            pending = [v for v in pending if v != '/']
        else:
            done.append(component)
    return root.joinpath(*done)


def mapped(path):
    path = str(path).lstrip('/')
    return 'usr/' + path if path.split('/')[0] in ('bin', 'sbin', 'lib') else path


def inventory(root):
    out = {}
    for p in walk(root):
        name = p.relative_to(root).as_posix()
        s = p.lstat()
        entry = {'mode': stat.S_IMODE(s.st_mode)}
        if p.is_symlink():
            entry.update(kind='link', target=os.readlink(p))
            target = resolve(root, name)
            entry['resolved'] = target.relative_to(root).as_posix()
            if target.is_file():
                entry['resolved_sha256'] = sha(target)
        elif stat.S_ISREG(s.st_mode):
            entry.update(kind='file', sha256=sha(p), bytes=s.st_size)
        elif stat.S_ISDIR(s.st_mode):
            entry['kind'] = 'directory'
        else:
            entry.update(kind='special', rdev=s.st_rdev, filetype=stat.S_IFMT(s.st_mode))
        out[name] = entry
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--resolv-policy', type=Path, required=True)
    ap.add_argument('--report', type=Path, required=True)
    a = ap.parse_args()
    source = a.source.resolve(strict=True)
    output = a.output.absolute()
    if source == Path('/') or not (source / 'rom/etc').is_dir():
        raise SystemExit('Requires an offline ASUS rootfs with rom/etc')
    if output.exists() or output.is_symlink():
        raise SystemExit('Output must not exist')
    if source in output.parents or output in source.parents:
        raise SystemExit('Source and output must be separate trees')
    for name in ('bin', 'sbin', 'lib', 'usr'):
        if not (source / name).is_dir() or (source / name).is_symlink():
            raise SystemExit('Source must be unmerged: ' + name)
    before = inventory(source)
    policy = json.loads(a.resolv_policy.read_text())
    for key in ('lib/libresolv.so.2', 'usr/lib/libresolv.so.2'):
        if before[key]['sha256'] != policy[key]:
            raise SystemExit('Unreviewed libresolv input: ' + key)
    # Preflight every collision before creating the candidate.
    decisions = {}
    for name, entry in before.items():
        dest = mapped(name)
        if dest == name or dest not in before:
            continue
        other = before[dest]
        if entry['kind'] == other['kind'] == 'directory':
            continue
        if entry['kind'] == other['kind'] == 'file' and entry['sha256'] == other['sha256'] and entry['mode'] == other['mode']:
            decisions[name] = 'identical_file'
        elif entry['kind'] == 'link' and resolve(source, name) == resolve(source, dest):
            decisions[name] = 'existing_alias_to_destination'
        elif name == 'lib/libresolv.so.2':
            decisions[name] = 'keep_lib_copy_matched_to_active_glibc'
        else:
            raise SystemExit('Unreviewed collision: ' + name + ' -> ' + dest)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['cp', '-a', '--reflink=auto', str(source), str(output)], check=True)
    links_changed = []

    def merge(directory):
        for p in sorted(directory.iterdir()):
            rel = p.relative_to(output).as_posix()
            dest = output / mapped(rel)
            if p.is_dir() and not p.is_symlink():
                if dest.exists():
                    if dest.is_symlink() or not dest.is_dir():
                        raise RuntimeError('Unexpected destination: ' + str(dest))
                    merge(p)
                    p.rmdir()
                else:
                    # Recurse so every relative symlink is relocated explicitly.
                    dest.mkdir(mode=stat.S_IMODE(p.stat().st_mode))
                    dest.chmod(stat.S_IMODE(p.stat().st_mode))
                    merge(p)
                    p.rmdir()
                continue
            if rel in decisions:
                if decisions[rel] == 'keep_lib_copy_matched_to_active_glibc':
                    dest.unlink()
                else:
                    p.unlink()
                    continue
            if p.is_symlink():
                old = os.readlink(p)
                if not old.startswith('/'):
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(rel), old))
                    new = posixpath.relpath(mapped(target), posixpath.dirname(mapped(rel)))
                    if new != old:
                        p.unlink()
                        p.symlink_to(new)
                        links_changed.append({'path': rel, 'old': old, 'new': new})
            p.rename(dest)

    for name in ('bin', 'sbin', 'lib'):
        merge(output / name)
        (output / name).rmdir()
        (output / name).symlink_to('usr/' + name)
    after = inventory(output)
    failures = []
    preserved = 0
    for name, entry in before.items():
        target = resolve(output, name)
        if entry['kind'] == 'file':
            expected = policy['lib/libresolv.so.2'] if name == 'usr/lib/libresolv.so.2' else entry['sha256']
            mode = before['lib/libresolv.so.2']['mode'] if name == 'usr/lib/libresolv.so.2' else entry['mode']
            if not target.is_file() or sha(target) != expected or stat.S_IMODE(target.stat().st_mode) != mode:
                failures.append(name)
            else:
                preserved += name != 'usr/lib/libresolv.so.2'
        elif entry['kind'] == 'link' and 'resolved_sha256' in entry:
            if not target.is_file() or sha(target) != entry['resolved_sha256']:
                failures.append(name)
    report = {'source_inventory': before, 'output_inventory': after,
              'decisions': decisions, 'rewritten_relative_links': links_changed,
              'preserved_regular_paths': preserved, 'failures': failures,
              'glibc_rebuild_installed': False, 'ubuntu_package_installed': False,
              'source_unchanged': inventory(source) == before}
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, indent=2) + '\n')
    if failures or not report['source_unchanged']:
        raise SystemExit('Preservation failed; inspect report')
    print(json.dumps({k: v for k, v in report.items() if not k.endswith('_inventory')}, indent=2))


if __name__ == '__main__':
    main()
