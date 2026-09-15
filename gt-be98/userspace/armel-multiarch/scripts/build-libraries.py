#!/usr/bin/env python3
"""Rebuild the existing C library versions with isolated Ubuntu GCC 15 armel."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--router-sources', type=Path, required=True)
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--components', nargs='+', choices=['zlib', 'expat', 'json-c', 'libcap-ng'], default=['zlib', 'expat', 'json-c', 'libcap-ng'])
a = p.parse_args()
tc = a.toolchain.resolve(strict=True)
out = a.output.absolute()
if out.exists():
    p.error('output must not exist')
out.mkdir(parents=True)
cc = str(tc/'usr/bin/arm-linux-gnueabi-gcc-15')
env = dict(os.environ)
env.update(PATH=str(tc/'usr/bin')+':'+env['PATH'],
           LD_LIBRARY_PATH=str(tc/'usr/lib/aarch64-linux-gnu'),
           CC=cc+' --sysroot='+str(tc), AR='arm-linux-gnueabi-ar',
           CXX=str(tc/'usr/bin/arm-linux-gnueabi-g++-15')+' --sysroot='+str(tc),
           RANLIB='arm-linux-gnueabi-ranlib', STRIP='arm-linux-gnueabi-strip',
           CFLAGS='-O2 -fPIC -std=gnu11 -mcpu=cortex-a53 -mfpu=neon-fp-armv8 -mfloat-abi=softfp -U_TIME_BITS -U_FILE_OFFSET_BITS',
           LDFLAGS='-static-libgcc')
versions = {'zlib': 'zlib', 'expat': 'expat-2.0.1', 'json-c': 'json-c', 'libcap-ng': 'libcap-ng'}
artifacts = {'zlib': ('libz.so.1.2.12', 'libz.so.1'),
             'expat': ('.libs/libexpat.so.1.5.2', 'libexpat.so.1.5.2'),
             'json-c': ('.libs/libjson-c.so.2.0.2', 'libjson-c.so.2.0.2'),
             'libcap-ng': ('src/.libs/libcap-ng.so.0.0.0', 'libcap-ng.so.0.0.0')}
(out/'rebuilt').mkdir()
report = {'compiler': subprocess.check_output([cc, '--version'], text=True).splitlines()[0],
          'cflags': env['CFLAGS'], 'ldflags': env['LDFLAGS'], 'components': {}}
for name, relative in versions.items():
    if name not in a.components:
        continue
    src = a.router_sources.resolve(strict=True)/relative
    work = out/name
    shutil.copytree(src, work, symlinks=True)
    if name == 'json-c':
        policy = json.loads((Path(__file__).resolve().parents[1]/'patches/json-c-gcc15.json').read_text())
        current = [hashlib.sha256((work/fix['file']).read_bytes()).hexdigest() for fix in policy['files']]
        if current == [fix['before_sha256'] for fix in policy['files']]:
            patch = Path(__file__).resolve().parents[1]/'patches/json-c-gcc15.patch'
            subprocess.run(['patch', '-p5', '--batch', '-i', str(patch)], cwd=work, check=True)
        elif current != [fix['after_sha256'] for fix in policy['files']]:
            raise RuntimeError('unreviewed json-c source')
        assert all(hashlib.sha256((work/fix['file']).read_bytes()).hexdigest() == fix['after_sha256'] for fix in policy['files'])
    with (out/(name+'.log')).open('w') as log:
        # Remove prior configured artifacts only from the disposable source copy.
        subprocess.run(['make', 'distclean'], cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT)
        for f in ('config.cache', 'config.status'):
            (work/f).unlink(missing_ok=True)
        if name == 'libcap-ng':
            # The repository omits this GNU Automake documentation placeholder.
            # Create it only in the disposable build copy, as the legacy build did.
            (work/'NEWS').touch(exist_ok=True)
        if name in ('json-c', 'libcap-ng'):
            subprocess.run(['autoreconf', '-fi'], cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        cmd = ['./configure', '--prefix=/usr', '--libdir=/usr/lib/arm-linux-gnueabi']
        if name == 'zlib':
            cmd += ['--shared']
        else:
            cmd += ['--host=arm-linux-gnueabi', '--build=aarch64-linux-gnu', '--enable-shared', '--disable-static']
        if name == 'libcap-ng':
            cmd += ['--without-python', '--without-python3', '--disable-swig']
        subprocess.run(cmd, cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        target = ['libexpat.la'] if name == 'expat' else []
        subprocess.run(['make', '-j4', *target], cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    libs = []
    for f in sorted(work.rglob('*.so*')):
        if f.is_file() and not f.is_symlink():
            with f.open('rb') as s:
                if s.read(4) != b'\x7fELF':
                    continue
            libs.append({'path': str(f.relative_to(out)), 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()})
    report['components'][name] = {'source_directory': relative, 'shared_libraries': libs}
    built, installed_name = artifacts[name]
    shutil.copy2(work/built, out/'rebuilt'/installed_name)
    subprocess.run(['arm-linux-gnueabi-strip', '--strip-unneeded', str(out/'rebuilt'/installed_name)], env=env, check=True)
    artifact = out/'rebuilt'/installed_name
    report['components'][name]['installed'] = {
        'file': installed_name, 'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
        'bytes': artifact.stat().st_size}
    (out/'build-report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(name, 'built', len(libs), 'libraries', flush=True)
