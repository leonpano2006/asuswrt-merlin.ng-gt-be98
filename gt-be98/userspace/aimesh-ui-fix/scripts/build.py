#!/usr/bin/env python3
"""Rebuild header consumers; retain the latest HTTPD and platform-rc object sets."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

r = Path(__file__).resolve().parents[1]
w = r.parent
integration = w / 'rmerlin-integration-20260916'
router = integration / 'source-tree/release/src/router'
platform = w / 'systemd-rc-platform-20260917'
t = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env = dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir'])
records = {}

for component, names in [('httpd', ['web']), ('rc', ['init', 'wan', 'services'])]:
    out = r / 'build' / component
    out.mkdir(exist_ok=True)
    templates = json.loads((integration / 'build' / ('management-' + component) / 'compile-commands.json').read_text())
    commands = []
    for name in names:
        original = router / component / (name + '.c')
        source = r / 'src/web.c' if name == 'web' else platform / 'src/services.c' if name == 'services' else original
        cmd = next(c[:] for c in templates if str(original) in c)
        cmd[cmd.index(str(original))] = str(source)
        cmd[1:1] = ['-I' + str(r / 'src'), '-I' + str(platform / 'src'), '-I' + str(original.parent)]
        cmd[cmd.index('-o') + 1] = str(out / (name + '.o'))
        cmd[cmd.index('-MF') + 1] = str(out / (name + '.d'))
        commands.append(cmd)
    if component == 'httpd':
        link = json.loads((w / 'rmerlin-httpd-fix-20260917/evidence/build.json').read_text())['link']
    else:
        link = next(c[:] for c in json.loads((platform / 'evidence/rc-build.json').read_text())['commands']
                    if '-o' in c and c[c.index('-o') + 1] == str(platform / 'build/rc/rc'))
    link[link.index('-o') + 1] = str(out / component)
    for name in names:
        idx = next(i for i, val in enumerate(link) if val.endswith('/' + name + '.o'))
        link[idx] = str(out / (name + '.o'))
    commands.append(link)
    for i, cmd in enumerate(commands):
        with (r / 'evidence' / ('build-%s-%d.log' % (component, i))).open('w') as log:
            subprocess.run(cmd, cwd=router / component, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    subprocess.run([t['tools'] + 'strip', '--strip-unneeded', '-o', str(out / (component + '.stripped')), str(out / component)], env=env, check=True)
    records[component] = {'commands': commands, 'sha256': hashlib.sha256((out / (component + '.stripped')).read_bytes()).hexdigest()}
    print('REBUILT', component, records[component]['sha256'], flush=True)
(r / 'evidence/build.json').write_text(json.dumps(records, indent=2) + '\n')
