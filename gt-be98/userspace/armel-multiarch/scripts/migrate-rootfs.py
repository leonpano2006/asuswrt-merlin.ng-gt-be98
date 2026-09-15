#!/usr/bin/env python3
"""Classify libraries in a new offline image, preserving old firmware paths."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import stat
import subprocess
from elftools.elf.elffile import ELFFile

ARMEL = 'usr/lib/arm-linux-gnueabi'
ARM64 = 'usr/lib/aarch64-linux-gnu'
PRIVATE = ('ipsec', 'l2tp', 'libnl', 'netatalk', 'pppd', 'xtables')

def configure_loader(root):
    conf = root/'rom/etc/ld.so.conf'
    directory = root/'rom/etc/ld.so.conf.d'
    directory.mkdir(mode=0o755, exist_ok=True)
    content = {'libc.conf': '/usr/local/lib\n',
               'zz-legacy.conf': '/opt/lib\n/opt/usr/lib\n/lib\n/usr/lib\n'}
    for triplet in ('arm-linux-gnueabi', 'arm-linux-gnueabihf', 'aarch64-linux-gnu'):
        content[triplet+'.conf'] = '/usr/local/lib/'+triplet+'\n/usr/lib/'+triplet+'\n'
    for name, data in content.items():
        p = directory/name
        if p.exists() and p.read_text() != data:
            raise ValueError('unreviewed loader fragment: '+name)
        p.write_text(data)
        p.chmod(0o644)
    conf.write_text('include /etc/ld.so.conf.d/*.conf\n')
    return sorted('rom/etc/ld.so.conf.d/'+name for name in content)

def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def resolve(root, name):
    pending = list(PurePosixPath('/' + str(name).lstrip('/')).parts[1:])
    done = []
    links = 0
    while pending:
        part = pending.pop(0)
        if part in ('', '.', '/'):
            continue
        if part == '..':
            if done:
                done.pop()
            continue
        p = root.joinpath(*done, part)
        if p.is_symlink():
            links += 1
            if links > 40:
                raise ValueError('symlink loop: ' + str(name))
            target = os.readlink(p)
            if target.startswith('/'):
                done = []
            pending = list(PurePosixPath(target).parts) + pending
        else:
            done.append(part)
    return root.joinpath(*done)

def abi(p):
    if not p.is_file() or p.is_symlink():
        return None
    with p.open('rb') as f:
        if f.read(4) != b'\x7fELF':
            return None
        f.seek(0)
        e = ELFFile(f)
        if e.header['e_machine'] == 'EM_ARM':
            return 'armhf' if e.header['e_flags'] & 0x400 else 'armel'
        if e.header['e_machine'] == 'EM_AARCH64':
            return 'aarch64'
        return 'other'

def entries(root):
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            yield Path(directory) / name

def migrate(source, output):
    source = source.resolve(strict=True)
    output = output.absolute()
    if source == Path('/') or not (source/'rom/etc').is_dir():
        raise ValueError('offline ASUS rootfs required')
    if output.exists() or output.is_symlink() or source in output.parents or output in source.parents:
        raise ValueError('output must be a new separate tree')
    if not (source/'lib').is_symlink() or os.readlink(source/'lib') != 'usr/lib':
        raise ValueError('requires the verified merged-/usr layout')
    if (source/ARMEL).exists() or (source/ARMEL).is_symlink():
        raise ValueError('armel multiarch destination already exists')
    plan = {}
    other_abi = []
    for p in sorted((source/'usr/lib').iterdir()):
        kind = abi(p)
        if kind == 'armel':
            plan[p.relative_to(source).as_posix()] = ARMEL + '/' + p.name
        elif kind == 'aarch64':
            other_abi.append({'path': p.relative_to(source).as_posix(), 'sha256': sha(p)})
        elif kind:
            raise ValueError('unexpected flat ELF ABI: ' + str(p))
    for name in PRIVATE:
        directory = source/'usr/lib'/name
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError('expected private directory: ' + name)
        observed = {abi(p) for p in entries(directory)} - {None}
        if observed != {'armel'}:
            raise ValueError('mixed or unknown private directory: ' + name)
        plan['usr/lib/' + name] = ARMEL + '/' + name
    # Move each SONAME/development alias alongside its real file.
    for p in sorted((source/'usr/lib').iterdir()):
        if p.is_symlink():
            real = resolve(source, p.relative_to(source)).relative_to(source).as_posix()
            if real in plan:
                plan[p.relative_to(source).as_posix()] = posixpath.dirname(plan[real]) + '/' + p.name
    def mapped(name):
        for old, new in plan.items():
            if name == old or name.startswith(old + '/'):
                return new + name[len(old):]
        return name
    coalesced = set()
    for old, new in plan.items():
        if (source/new).exists() or (source/new).is_symlink():
            a, b = resolve(source, old), resolve(source, new)
            if a.is_file() and b.is_file() and sha(a) == sha(b) and stat.S_IMODE(a.stat().st_mode) == stat.S_IMODE(b.stat().st_mode):
                coalesced.add(old)
            else:
                raise ValueError('destination collision: ' + new)
    before = {}
    symlinks = {}
    for p in entries(source):
        name = p.relative_to(source).as_posix()
        if p.is_symlink():
            symlinks[name] = os.readlink(p)
            target = resolve(source, name)
            if target.is_file():
                before[name] = (sha(target), stat.S_IMODE(target.stat().st_mode))
        elif p.is_file():
            before[name] = (sha(p), stat.S_IMODE(p.stat().st_mode))
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['cp', '-a', '--reflink=auto', str(source), str(output)], check=True)
    (output/ARMEL).mkdir(mode=0o755)
    for old, new in sorted(plan.items()):
        if old in coalesced:
            (output/old).unlink()
        else:
            (output/old).rename(output/new)
        (output/old).symlink_to(posixpath.relpath(new, posixpath.dirname(old)))
    # Retarget relative links relocated with libraries/private directories.
    for old, target in symlinks.items():
        new = mapped(old)
        if new == old or old in coalesced or target.startswith('/'):
            continue
        target_name = posixpath.normpath(posixpath.join(posixpath.dirname(old), target))
        target_new = posixpath.relpath(mapped(target_name), posixpath.dirname(new))
        p = output/new
        p.unlink()
        p.symlink_to(target_new)
    checked = 0
    for old, expected in before.items():
        actual = resolve(output, old)
        if not actual.is_file() or (sha(actual), stat.S_IMODE(actual.stat().st_mode)) != expected:
            raise ValueError('original path no longer resolves identically: ' + old)
        checked += 1
    loader_fragments = configure_loader(output)
    modules = [p for p in entries(source) if p.is_file() and not p.is_symlink() and p.suffix == '.ko']
    assert all(sha(p) == sha(output/p.relative_to(source)) for p in modules)
    assert not any(abi(p) == 'armel' for p in (output/'usr/lib').iterdir())
    return {'schema': 1, 'moves': plan, 'real_files_and_aliases_preserved': checked,
            'identical_duplicates_coalesced': sorted(coalesced),
            'modules_unchanged': len(modules), 'flat_armel_elf_files_remaining': 0,
            'other_abi_flat_files_retained': other_abi,
            'armel_real_files': sum(abi(p) == 'armel' for p in entries(output/ARMEL)),
            'loader_entry': '/lib/ld-linux.so.3 -> arm-linux-gnueabi/ld-linux.so.3',
            'configuration_change': 'Ubuntu-style include and per-ABI loader configuration fragments',
            'loader_fragments': loader_fragments,
            'legacy_alias_policy': 'retain old file/private-directory paths for existing vendor ABI consumers'}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    if a.report.exists():
        p.error('report already exists')
    report = migrate(a.source, a.output)
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'moves'}, indent=2))
