#!/usr/bin/env python3
"""Build pinned upstream OpenSSL on DGX with GCC 15 and the firmware ARMEL ABI."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import time

r = Path(__file__).resolve().parents[1]
w = r.parent
t = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
source = r / 'sources/release/src/router/openssl-3.5'
build = r / 'build/openssl-armel'
build.mkdir(exist_ok=False)
stage = r / 'build/openssl-armel-stage'
env = dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir'], CC=t['cc'],
           AR=t['tools'] + 'ar', RANLIB=t['tools'] + 'ranlib', NM=t['tools'] + 'nm')
commands = []
started = time.monotonic()
def run(command, name, cwd=build):
    commands.append(command)
    (r / 'evidence/openssl-build-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    with (r / 'evidence' / (name + '.log')).open('w') as log:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print((r / 'evidence' / (name + '.log')).read_text()[-6000:], flush=True)
        raise SystemExit(result.returncode)

assert os.uname().machine == 'aarch64'
run(['perl', str(source / 'Configure'), 'linux-bcmarm', '--prefix=/usr',
     '--openssldir=/etc', '--libdir=lib/arm-linux-gnueabi',
     '-Os', '-g', '-frecord-gcc-switches', '-fstack-protector-strong',
     '-ffunction-sections', '-fdata-sections', '-Wl,--gc-sections',
     '-Wl,--build-id=sha1', 'shared', 'no-ssl2', 'no-gost', 'no-heartbeats',
     'no-err', 'no-async', 'no-tests', 'no-docs', '--api=1.1.1',
     'no-aria', 'no-sm2', 'no-sm3', 'no-sm4', '--with-rand-seed=devrandom'], 'openssl-configure')
run(['make', '-j8'], 'openssl-make')
run(['make', 'DESTDIR=' + str(stage), 'install_sw'], 'openssl-install')
files = {}
for name in ['libcrypto.so.3', 'libssl.so.3', 'apps/openssl', 'providers/legacy.so']:
    p = build / name
    files[name] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
record = {'completed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'elapsed_seconds': round(time.monotonic() - started, 2), 'compiler': t,
          'source_commit': '96831be75b3b891f6aa4c608f00cc7bb2d499d67',
          'source_version': (source / 'VERSION.dat').read_text(), 'files': files,
          'built_on': os.uname().nodename, 'router_modified': False}
(r / 'evidence/openssl-build.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2), flush=True)
