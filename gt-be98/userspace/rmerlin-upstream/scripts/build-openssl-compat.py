#!/usr/bin/env python3
from pathlib import Path
import difflib
import hashlib
import json
import os
import subprocess
import tarfile

r = Path(__file__).resolve().parents[1]
t = json.loads((r.parent / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env = dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir'])
source = r / 'sources/release/src/router/openssl11-compat'
out = r / 'build/openssl11-compat'
out.mkdir(exist_ok=True)
commands = []
patch = ''
flags = ['-std=gnu11', '-fPIC', '-Os', '-g', '-Wall', '-Wno-deprecated-declarations',
         '-D_FORTIFY_SOURCE=2', '-fstack-protector-strong', '-fvisibility=hidden',
         '-fno-semantic-interposition', '-Wformat', '-Wformat-security', '-frecord-gcc-switches',
         '-I' + str(r / 'build/openssl-armel/include'),
         '-I' + str(r / 'sources/release/src/router/openssl-3.5/include')]
with tarfile.open(r / 'openssl11-compat.tar') as archive:
    for part in ['crypto', 'ssl']:
        name = 'release/src/router/openssl11-compat/' + part + '_compat.c'
        original = archive.extractfile(name).read().decode()
        path = source / (part + '_compat.c')
        patch += ''.join(difflib.unified_diff(original.splitlines(True), path.read_text().splitlines(True),
                         fromfile='a/' + name, tofile='b/' + name))
        obj = out / (part + '_compat.o')
        command = [t['cc']] + flags + ['-c', str(path), '-o', str(obj)]
        commands.append(command)
        with (out / (part + '-compile.log')).open('w') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        lib = 'lib' + part + '.so.1.1'
        command = [t['cc'], '-shared', '-Wl,--build-id=sha1', '-Wl,--gc-sections,--as-needed',
                   '-Wl,-Bsymbolic-functions,-z,defs,-z,relro,-z,now,-z,noexecstack',
                   '-Wl,-soname,' + lib, '-Wl,--version-script=' + str(source / ('lib' + part + '.map')),
                   '-o', str(out / lib), str(obj), '-ldl']
        commands.append(command)
        with (out / (part + '-link.log')).open('w') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
(r / 'patches/openssl-compat-multiarch.patch').write_text(patch)
(r / 'evidence/openssl-compat-build.json').write_text(json.dumps({
    'compiler': t, 'commands': commands,
    'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.so.1.1')}
}, indent=2) + '\n')
print('OPENSSL_COMPAT_BUILT')
