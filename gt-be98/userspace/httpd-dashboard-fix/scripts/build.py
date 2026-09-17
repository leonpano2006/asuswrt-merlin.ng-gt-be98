#!/usr/bin/env python3
"""Rebuild only shared/misc.o with the recorded ARMEL target and link inputs."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

r = Path(__file__).resolve().parents[1]
w = r.parent
p = w / 'rmerlin-integration-20260916'
source = p / 'source-tree/release/src/router/shared/misc.c'
t = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env = dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir'])
commands = json.loads((p / 'build/management-shared/compile-commands.json').read_text())
cmd = next(c[:] for c in commands if str(source) in c)
cmd[cmd.index(str(source))] = str(r / 'src/misc.c')
cmd += ['-I' + str(source.parent)]
cmd[cmd.index('-o') + 1] = str(r / 'build/misc.o')
cmd[cmd.index('-MF') + 1] = str(r / 'build/misc.d')
link = json.loads((p / 'build/management-shared/link-command.json').read_text())
link[link.index('-o') + 1] = str(r / 'build/libshared.so')
link[link.index(str(p / 'build/management-shared/misc.o'))] = str(r / 'build/misc.o')
for name, argv in [('compile-misc', cmd), ('link-shared', link)]:
    with (r / 'evidence' / (name + '.log')).open('w') as log:
        subprocess.run(argv, cwd=source.parent, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
subprocess.run([t['tools'] + 'strip', '--strip-unneeded', '-o',
                str(r / 'build/libshared.stripped.so'), str(r / 'build/libshared.so')], env=env, check=True)
digest = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
record = {'compiler': t, 'compile': cmd, 'link': link,
          'sha256': digest(r / 'build/libshared.stripped.so'),
          'retained_objects': {str(Path(a).relative_to(w)): digest(a)
                               for a in link if a.endswith('.o') and a != str(r / 'build/misc.o')}}
(r / 'evidence/build.json').write_text(json.dumps(record, indent=2) + '\n')
print('LIBSHARED_REBUILT', record['sha256'])
