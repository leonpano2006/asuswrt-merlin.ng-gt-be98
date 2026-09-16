#!/usr/bin/env python3
"""Rebuild the four pinned ARMEL C libraries with A53 Crypto and glibc 2.44."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--router-sources', type=Path, required=True)
p.add_argument('--armel-checkpoint', type=Path, required=True)
p.add_argument('--jobs', type=int, default=3)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
cfg = json.loads((root / 'configs/build-targets.json').read_text())['armel']
libgcc = root / 'builds/armel/gcc-runtime/arm-linux-gnueabi/libgcc'
assert (libgcc / 'libgcc.a').is_file()
out = root / 'builds/armel/c-libraries'
assert not out.exists()
out.mkdir()
driver = shlex.split(Path(cfg['cc']).read_text().splitlines()[1])[1:-1]
command = driver[:1] + ['-B' + str(libgcc) + '/', '-L' + str(libgcc)] + driver[1:]
wrapper = out / 'runtime-cc'
wrapper.write_text('#!/bin/sh\nexec ' + shlex.join(command) + ' "$@"\n')
wrapper.chmod(0o755)
env = dict(os.environ, LC_ALL='C', CC=str(wrapper),
           PATH=str(Path(cfg['tools']).parent) + ':' + os.environ['PATH'],
           LD_LIBRARY_PATH=cfg['host_library_dir'],
           CFLAGS='-O2 -g -frecord-gcc-switches -fPIC -std=gnu11 -U_TIME_BITS -U_FILE_OFFSET_BITS',
           LDFLAGS='-static-libgcc -Wl,--build-id=sha1')
for key in ('AR','AS','LD','NM','RANLIB','STRIP'):
    env[key] = cfg['tools'] + key.lower()
components = {'zlib': ('zlib', 'libz.so.1.2.12', 'libz.so.1'),
              'expat': ('expat-2.0.1', '.libs/libexpat.so.1.5.2', 'libexpat.so.1.5.2'),
              'json-c': ('json-c', '.libs/libjson-c.so.2.0.2', 'libjson-c.so.2.0.2'),
              'libcap-ng': ('libcap-ng', 'src/.libs/libcap-ng.so.0.0.0', 'libcap-ng.so.0.0.0')}
report = dict(compiler=cfg, runtime_wrapper=wrapper.read_text(),
              cflags=env['CFLAGS'], ldflags=env['LDFLAGS'], components={})
for name, (source_name, artifact, installed) in components.items():
    work = out / name
    source = a.router_sources.resolve(strict=True) / source_name
    files = {str(f.relative_to(source)): hashlib.sha256(f.read_bytes()).hexdigest()
             for f in sorted(source.rglob('*')) if f.is_file() and not f.is_symlink()}
    shutil.copytree(source, work, symlinks=True)
    if name == 'json-c':
        patchroot = a.armel_checkpoint.resolve(strict=True) / 'patches'
        policy = json.loads((patchroot / 'json-c-gcc15.json').read_text())
        current = [hashlib.sha256((work / fix['file']).read_bytes()).hexdigest() for fix in policy['files']]
        if current == [fix['before_sha256'] for fix in policy['files']]:
            subprocess.run(['patch', '-p5', '--batch', '-i', str(patchroot / 'json-c-gcc15.patch')], cwd=work, check=True)
        assert all(hashlib.sha256((work / fix['file']).read_bytes()).hexdigest() == fix['after_sha256'] for fix in policy['files'])
    with (root / 'evidence' / ('armel-build-' + name + '.log')).open('w') as log:
        subprocess.run(['make', 'distclean'], cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT)
        for stale in ('config.cache','config.status'):
            (work / stale).unlink(missing_ok=True)
        if name == 'libcap-ng':
            (work / 'NEWS').touch(exist_ok=True)
        if name in ('json-c', 'libcap-ng'):
            subprocess.run(['autoreconf', '-fi'], cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        command = ['./configure', '--prefix=/usr', '--libdir=/usr/lib/arm-linux-gnueabi']
        command += (['--shared'] if name == 'zlib' else
                    ['--host=arm-linux-gnueabi', '--build=aarch64-linux-gnu', '--enable-shared', '--disable-static'])
        if name == 'libcap-ng':
            command += ['--without-python', '--without-python3', '--disable-swig']
        subprocess.run(command, cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['make', '-j' + str(a.jobs)] + (['libexpat.la'] if name == 'expat' else []),
                       cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    built = work / artifact
    assert built.is_file()
    report['components'][name] = dict(source_files=files, source_directory=source_name,
                                     artifact=str(built.relative_to(root)), installed=installed,
                                     unstripped_sha256=hashlib.sha256(built.read_bytes()).hexdigest())
    (root / 'evidence/c-libraries-build.json').write_text(json.dumps(report, indent=2) + '\n')
    print('BUILT', name, flush=True)
