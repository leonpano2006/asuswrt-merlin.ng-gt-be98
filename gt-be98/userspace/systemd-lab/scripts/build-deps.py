#!/usr/bin/env python3
"""Build private host gperf and the two new runtime libraries; never install on host /usr."""
import json
import os
from pathlib import Path
import subprocess

r = Path(__file__).resolve().parents[1]
env = dict(os.environ, LC_ALL='C')
commands = []
def run(name, argv, cwd, environment=env):
    commands.append({'name': name, 'argv': argv, 'cwd': str(cwd)})
    (r / 'evidence/dependency-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    print(name, flush=True)
    with (r / 'evidence' / (name + '.log')).open('w') as log:
        p = subprocess.run(argv, cwd=cwd, env=environment, stdout=log, stderr=subprocess.STDOUT)
    if p.returncode:
        print((r / 'evidence' / (name + '.log')).read_text()[-6000:], flush=True)
        raise SystemExit(p.returncode)

gperf = r / 'build/gperf'
gperf.mkdir(exist_ok=True)
run('gperf-configure', [str(r / 'sources/gperf-3.1/configure'), '--prefix=' + str(r / 'host')], gperf)
run('gperf-build', ['make', '-j4'], gperf)
run('gperf-install', ['make', 'install'], gperf)
env['PATH'] = str(r / 'host/bin') + ':' + env['PATH']
cap = r / 'sources/libcap-2.76/libcap'
args = ['make', '-j4', 'CC=' + str(r / 'build/cc'), 'BUILD_CC=/usr/bin/gcc',
        'CFLAGS=-Os -g -fPIC -D_LIBPSX_PTHREAD_LINKAGE -frecord-gcc-switches',
        'LDFLAGS=-Wl,--build-id=sha1', 'PTHREADS=yes', 'GOLANG=no', 'PAM_CAP=no',
        'prefix=/usr', 'lib=lib/aarch64-linux-gnu']
run('libcap-build', args + ['all'], cap)
run('libcap-install-sdk', args + ['DESTDIR=' + str(r / 'sdk'), 'install'], cap)
run('libcap-install-stage', args + ['DESTDIR=' + str(r / 'stage'), 'install'], cap)
cryptsrc = r / 'sources/libxcrypt-4.4.38'
run('libxcrypt-autogen', ['sh', 'autogen.sh'], cryptsrc)
crypt = r / 'build/libxcrypt'
crypt.mkdir(exist_ok=True)
cenv = dict(env, CC=str(r / 'build/cc'), CFLAGS='-Os -g -frecord-gcc-switches', LDFLAGS='-Wl,--build-id=sha1')
run('libxcrypt-configure', [str(cryptsrc / 'configure'), '--prefix=/usr', '--libdir=/usr/lib/aarch64-linux-gnu',
    '--host=aarch64-linux-gnu', '--build=aarch64-build-linux-gnu', '--disable-static',
    '--disable-obsolete-api', '--disable-werror'], crypt, cenv)
run('libxcrypt-build', ['make', '-j4'], crypt, cenv)
run('libxcrypt-install-sdk', ['make', 'DESTDIR=' + str(r / 'sdk'), 'install'], crypt, cenv)
run('libxcrypt-install-stage', ['make', 'DESTDIR=' + str(r / 'stage'), 'install'], crypt, cenv)
print('DEPENDENCIES_BUILT', flush=True)
