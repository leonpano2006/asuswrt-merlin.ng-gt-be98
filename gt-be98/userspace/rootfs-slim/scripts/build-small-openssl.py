#!/usr/bin/env python3
"""Isolated full-feature OpenSSL 4.0.2 size experiment; never install on router."""
import hashlib, json, os, shutil, subprocess, time
from pathlib import Path

r = Path(__file__).resolve().parents[1]
w = r.parent
old = w / 'userspace-refresh-20260917'
build = r / 'build/openssl-oz-lto'
build.mkdir(parents=True, exist_ok=False)
(r / 'evidence').mkdir(exist_ok=True)
assert hashlib.sha256((old/'sources/openssl-4.0.2.tar.gz').read_bytes()).hexdigest() == '736b467530f916737b7031310ccb21d8218c6229e61e8e160cd1d3458cd543a8'
plugin = w / 'gcc162-usb/obj/gcc/liblto_plugin.so'
env = dict(os.environ, CC=str(old/'build/cc'), LC_ALL='C',
           AR=f'/usr/bin/aarch64-linux-gnu-ar --plugin={plugin}',
           RANLIB=f'/usr/bin/aarch64-linux-gnu-ranlib --plugin={plugin}')
env.pop('LD_LIBRARY_PATH', None)
commands = [
    ['perl', str(old/'sources/openssl-4.0.2/Configure'), 'linux-aarch64',
     '--prefix=/usr', '--openssldir=/usr/lib/ssl/openssl4', '--libdir=lib/aarch64-linux-gnu',
     'shared', '-Oz', '-flto=8', '-g', '-frecord-gcc-switches',
     '-fstack-protector-strong', '-Wl,--build-id=sha1,-z,relro,-z,now'],
    ['make', '-j8', 'build_sw']]
start = time.monotonic()
for i, command in enumerate(commands):
    print('BUILD_STEP', i, flush=True)
    with (r/f'evidence/build-{i}.log').open('w') as log:
        p = subprocess.run(command, cwd=build, env=env, stdout=log, stderr=subprocess.STDOUT)
    if p.returncode:
        print((r/f'evidence/build-{i}.log').read_text()[-6000:]); raise SystemExit(p.returncode)
overlay = r/'overlay'
shutil.copytree(old/'overlay', overlay)
mapping = {'libcrypto.so.4':'usr/lib/aarch64-linux-gnu/libcrypto.so.4',
           'libssl.so.4':'usr/lib/aarch64-linux-gnu/libssl.so.4',
           'providers/legacy.so':'usr/lib/aarch64-linux-gnu/ossl-modules/legacy.so',
           'apps/openssl':'usr/libexec/openssl4'}
files = {}
for src, dst in mapping.items():
    target = overlay/dst
    shutil.copy2(build/src, target)
    target.chmod((old/'overlay'/dst).stat().st_mode & 0o7777)
    subprocess.run(['aarch64-linux-gnu-strip','--strip-unneeded',str(target)],check=True)
    files[dst] = {'bytes':target.stat().st_size,
                  'original_bytes':(old/'overlay'/dst).stat().st_size,
                  'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
record = {'commands':commands, 'env_overrides':{k:env[k] for k in ['CC','AR','RANLIB']},
          'elapsed_seconds':time.monotonic()-start, 'files':files,
          'features_disabled':[], 'router_modified':False}
(r/'evidence/optimized-build.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(files,indent=2))
