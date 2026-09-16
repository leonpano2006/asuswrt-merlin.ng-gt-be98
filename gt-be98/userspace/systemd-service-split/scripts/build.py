#!/usr/bin/env python3
"""Rebuild services.c and its dispatcher, retaining verified trial3 objects."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

r = Path(__file__).resolve().parents[1]; w = r.parent
parent = w / 'systemd-trial3-20260916'
t = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env = dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir'])
out = r / 'build/rc'; out.mkdir(exist_ok=True)
probes = r / 'build/probes'; probes.mkdir(exist_ok=True)
commands = []
def run(cmd, name):
    commands.append(cmd)
    with (r / 'evidence' / (name + '.log')).open('w') as log:
        result = subprocess.run(cmd, cwd=r / 'sources/rc', env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print((r / 'evidence' / (name + '.log')).read_text()[-6000:])
        raise SystemExit(result.returncode)

prior = json.loads((parent / 'evidence/rc-compile-commands.json').read_text())
command = next(x for x in prior if x[x.index('-c') + 1].endswith('/services.c'))
command = [x.replace(str(parent / 'sources/rc'), str(r / 'sources/rc'))
             .replace(str(parent / 'build/rc'), str(out)) for x in command]
command.insert(1, '-I' + str(r / 'src'))
run(command, 'services-build')
small = [t['cc'], '-std=gnu11', '-O2', '-g', '-Wall', '-Wextra', '-Werror',
         '-I' + str(r / 'src'), '-I' + str(parent / 'src'),
         '-frecord-gcc-switches', '-Wl,--build-id=sha1']
run(small + ['-c', str(r / 'src/rc-services.c'), '-o', str(out / 'rc-services.o')], 'dispatcher-build')
link = json.loads((parent / 'evidence/rc-link-command.json').read_text())
retained = {}
for name in link:
    p = Path(name)
    if p.parent == parent / 'build/rc' and p.suffix == '.o' and p.name != 'services.o':
        shutil.copy2(p, out / p.name)
        retained[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
link = [x.replace(str(parent / 'build/rc'), str(out)) for x in link]
link.insert(link.index(str(out / 'services.o')) + 1, str(out / 'rc-services.o'))
run(link, 'rc-link')

# Use the actual modified services.c for the test entry points; discard unrelated
# functions and satisfy only the legacy launcher imports with counting stubs.
sections = command[:]
sections[sections.index('-o') + 1] = str(probes / 'services-sections.o')
sections += ['-ffunction-sections', '-fdata-sections']
run(sections, 'test-services-build')
run(small + [str(r / 'tests/service-probe.c'), str(probes / 'services-sections.o'),
    str(r / 'src/rc-services.c'), str(parent / 'src/rc-manager.c'), str(parent / 'src/rc-client.c'),
    '-Wl,--gc-sections,--wrap=leon_rc_managed', '-o', str(probes / 'service-probe')], 'service-probe-build')
(r / 'evidence/compile-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
(r / 'evidence/retained-objects.json').write_text(json.dumps(retained, indent=2) + '\n')
print('SERVICE_SPLIT_RC_BUILT', len(retained), 'unchanged objects')
