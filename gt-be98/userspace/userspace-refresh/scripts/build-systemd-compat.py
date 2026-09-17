#!/usr/bin/env python3
"""Compile the existing systemd 257 manager and credential tool against OpenSSL 4.

This is a compatibility probe, not a replacement production feature profile.
"""
import json
import os
from pathlib import Path
import subprocess
import time

r = Path(__file__).resolve().parents[1]
old = r.parent / 'systemd-upgrade-20260917'
(r / 'configs').mkdir(exist_ok=True)
cross = r / 'configs/systemd-openssl4.ini'
cross.write_text((old / 'configs/aarch64-sysroot.ini').read_text().replace(str(old), str(r)))
base = json.loads((old / 'evidence/systemd-commands.json').read_text())['commands'][0]
options = [x for x in base if x.startswith(('--prefix=', '--libdir=', '--sysconfdir=', '--localstatedir=', '--buildtype=', '-D'))]
options = [x for x in options if not x.startswith(('-Dversion-tag=', '-Dtests='))]
options += ['-Dversion-tag=257.13-gt-be98-openssl4-probe', '-Dtests=true', '-Dopenssl=enabled', '-Dcryptolib=openssl']
source = next((old / 'sources').glob('systemd-*/'))
build = r / 'build/systemd-openssl4'
assert not build.exists()
env = dict(os.environ, PATH=str(r.parent / 'systemd-lab-20260916/host/bin') + ':' + os.environ['PATH'], LC_ALL='C')
env.pop('LD_LIBRARY_PATH', None)
env.pop('PKG_CONFIG_PATH', None)
commands = [
    ['meson', 'setup', str(build), str(source), '--cross-file', str(cross)] + options,
    ['ninja', '-C', str(build), '-j4', 'systemd', 'systemd-executor', 'systemctl',
     'systemd-journald', 'journalctl', 'systemd-creds', 'test-openssl'],
]
start = time.monotonic()
record = {'purpose': 'compatibility only; not the completed systemd feature update', 'commands': commands,
          'source_modified': False, 'router_modified': False}
(r / 'evidence/systemd-openssl4-commands.json').write_text(json.dumps(record, indent=2) + '\n')
for name, command in zip(('configure', 'make'), commands):
    print('systemd-openssl4-' + name, flush=True)
    logfile = r / 'evidence' / ('systemd-openssl4-' + name + '.log')
    with logfile.open('w') as log:
        p = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    record[name + '_exit_code'] = p.returncode
    if p.returncode:
        print(logfile.read_text()[-6000:])
        break
record['elapsed_seconds'] = round(time.monotonic() - start, 2)
(r / 'evidence/systemd-openssl4-build.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({k: v for k, v in record.items() if k != 'commands'}, indent=2))
raise SystemExit(p.returncode)
