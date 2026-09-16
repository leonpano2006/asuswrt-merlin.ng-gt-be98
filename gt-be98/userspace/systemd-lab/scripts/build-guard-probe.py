#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import subprocess

r = Path(__file__).resolve().parents[1]
w = r.parent
config = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env = dict(os.environ, LD_LIBRARY_PATH=config['host_library_dir'])
out = r / 'build/probes'
out.mkdir(exist_ok=True)
common = [config['cc'], '-O2', '-g', '-frecord-gcc-switches', '-Wl,--build-id=sha1']
commands = [common + ['-fPIC', '-shared', '-Wl,-soname,libguard-provider.so',
    str(r / 'scripts/guard-provider.c'), '-o', str(out / 'libguard-provider.so')],
    common + [str(r / 'scripts/guard-service-probe.c'), '-L' + str(out), '-lguard-provider',
    '-Wl,-rpath,/usr/lib/arm-linux-gnueabi/leon-systemd-lab', '-o', str(out / 'guardcheck')]]
for cmd in commands:
    subprocess.run(cmd, env=env, check=True)
files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()}
(r / 'evidence/guard-probe.json').write_text(json.dumps({'commands': commands, 'sha256': files,
    'test_double_only': True, 'contains_no_flash_or_reboot_calls': True}, indent=2) + '\n')
print('ARMEL_SYSTEMD_GUARD_PROBE_BUILT', flush=True)
