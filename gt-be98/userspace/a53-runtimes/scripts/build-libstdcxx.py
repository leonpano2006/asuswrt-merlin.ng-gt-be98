#!/usr/bin/env python3
"""Build matching shared C++ runtimes against our new libgcc and glibc 2.44."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('abi', choices=['armel', 'armhf', 'aarch64'])
p.add_argument('--jobs', type=int, default=4)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
ws = root.parent
cfg = json.loads((root / 'configs/build-targets.json').read_text())[a.abi]
env = dict(os.environ, LC_ALL='C')
if cfg['host_library_dir']:
    env['LD_LIBRARY_PATH'] = cfg['host_library_dir']
env['PATH'] = str(Path(cfg['tools']).parent) + ':' + env['PATH']
source = (ws / 'gcc162-usb/gcc-16.2.0' if a.abi == 'aarch64'
          else root / 'sources/gcc-15.2.0')
libgcc = root / 'builds' / a.abi / 'gcc-runtime' / cfg['triplet'] / 'libgcc'
assert (libgcc / 'libgcc_s.so.1').is_file() and (libgcc / 'libgcc.a').is_file()
obj = libgcc.parent / 'libstdc++-v3'
obj.mkdir(exist_ok=True)
# Insert the new runtime before *all* compiler-default library search paths.
# Use gcc as the C++ driver, as GCC's top-level build does: it invokes cc1plus
# for .cc/.cpp while avoiding a dependency on an already-installed libstdc++.
driver = shlex.split(Path(cfg['cc']).read_text().splitlines()[1])[1:-1]
command = driver[:1] + ['-B' + str(libgcc) + '/', '-L' + str(libgcc),
                        '-Wl,-rpath-link,' + str(libgcc)] + driver[1:]
wrapper = obj / 'runtime-cc'
wrapper.write_text('#!/bin/sh\nexec ' + shlex.join(command) + ' "$@"\n')
wrapper.chmod(0o755)
env.update(CC=str(wrapper), CXX=str(wrapper) + ' -shared-libgcc -nostdinc++',
           CFLAGS='-O2 -g -frecord-gcc-switches',
           CXXFLAGS='-O2 -g -frecord-gcc-switches',
           LDFLAGS='-Wl,--build-id=sha1 -Wl,-Map=' + str(obj / 'link.map'))
for key in ('AR', 'AS', 'LD', 'NM', 'RANLIB', 'STRIP'):
    env[key] = cfg['tools'] + key.lower()
commands = []

def run(args, label):
    command = [str(x) for x in args]
    commands.append(command)
    record = dict(commands=commands, cwd=str(obj),
                  environment={k: env[k] for k in ('CC','CXX','CFLAGS','CXXFLAGS','LDFLAGS')},
                  runtime_wrapper=wrapper.read_text())
    (root / 'evidence' / (a.abi + '-libstdcxx-commands.json')).write_text(json.dumps(record, indent=2) + '\n')
    print(a.abi, label, flush=True)
    with (root / 'evidence' / (a.abi + '-' + label + '.log')).open('w') as log:
        subprocess.run(command, cwd=obj, env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True)

if not (obj / 'Makefile').exists():
    run([source / 'libstdc++-v3/configure', '--build=aarch64-build-linux-gnu',
         '--host=' + cfg['triplet'], '--target=' + cfg['triplet'],
         '--prefix=/usr', '--libdir=/usr/lib/' + cfg['triplet'],
         '--with-gxx-include-dir=/usr/include/c++/' + cfg['compiler_version'],
         '--disable-multilib', '--enable-shared', '--enable-static',
         '--disable-nls', '--disable-libstdcxx-pch', '--enable-clocale=gnu',
         '--enable-c99', '--enable-libstdcxx-time=yes', '--enable-libstdcxx-threads',
         '--enable-libstdcxx-dual-abi', '--with-default-libstdcxx-abi=new',
         '--enable-symvers=gnu', '--enable-tls', '--disable-werror'], 'configure-libstdcxx')
# Standalone builds still require the normal ../libgcc layout for gthr-default.h.
# Do not accept a silent configure fallback to a C++ runtime without threads.
assert '#define _GLIBCXX_HAS_GTHREADS 1' in (obj / 'config.h').read_text()
run(['make', '-j' + str(a.jobs)], 'build-libstdcxx')
assert (obj / 'src/.libs/libstdc++.so.6').resolve(strict=True).is_file()
print('BUILT', (obj / 'src/.libs/libstdc++.so.6').resolve(), flush=True)
