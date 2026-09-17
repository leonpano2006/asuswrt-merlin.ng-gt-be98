#!/usr/bin/env python3
"""Build upstream less natively on DGX against the router glibc/tinfo ABI."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

r = Path(__file__).resolve().parents[1]
obj = r / 'build/obj'
obj.mkdir(exist_ok=False)
env = dict(os.environ, CC=str(r / 'build/cc'),
           CFLAGS='-Oz -flto -frecord-gcc-switches -fstack-protector-strong',
           CPPFLAGS='-D_FORTIFY_SOURCE=2',
           LDFLAGS='-flto -Wl,--as-needed -Wl,--build-id=sha1 -Wl,-z,relro,-z,now',
           SOURCE_DATE_EPOCH='1789560000')
commands = [
    [str(r / 'sources/less-704/configure'), '--prefix=/usr', '--sysconfdir=/etc',
     '--libexecdir=/usr/bin', '--with-regex=posix'],
    ['make', '-j8'], ['make', 'install', 'DESTDIR=' + str(r / 'stage')],
]
for name, command in zip(('configure', 'make', 'install'), commands):
    with (r / 'evidence' / (name + '.log')).open('w') as log:
        subprocess.run(command, cwd=obj, env=env, check=True,
                       stdout=log, stderr=subprocess.STDOUT)
for name in ('less', 'lesskey', 'lessecho'):
    file = r / 'stage/usr/bin' / name
    subprocess.run(['strip', '--strip-unneeded', str(file)], check=True)
    with (r / 'evidence' / (name + '-elf.txt')).open('w') as log:
        subprocess.run(['readelf', '-h', '-n', '-d', '-V', '-W', str(file)],
                       stdout=log, check=True)
with (r / 'evidence/compiler-switches.txt').open('w') as log:
    subprocess.run(['readelf', '-p', '.GCC.command.line', str(obj / 'main.o')],
                   stdout=log, check=True)
record = {'commands': commands, 'environment': {k: env[k] for k in
          ('CC', 'CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'SOURCE_DATE_EPOCH')},
          'installed': {p.relative_to(r / 'stage').as_posix(): {
              'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
              'bytes': p.stat().st_size}
              for p in (r / 'stage').rglob('*') if p.is_file()}}
(r / 'evidence/build.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record['installed'], indent=2))
