#!/usr/bin/env python3
"""Isolated AArch64 build of the existing ASUS BusyBox feature set."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

root = Path(__file__).resolve().parent
workspace = root.parent
previous = workspace / 'ping-diagnosis-20260922'
target = json.loads((workspace / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['aarch64']
build = root / 'build'
evidence = root / 'evidence'
build.mkdir(exist_ok=True)
evidence.mkdir(exist_ok=True)
sources = build / 'sources'
if sources.exists():
    raise SystemExit('Existing build sources retained; use a new directory for a fresh build.')
sources.mkdir()
inputs = {}
for name in ('bb-src.tgz', 'bb-kit.tar'):
    archive = Path('/home/leonpano/gcc16-a53') / name
    inputs[name] = hashlib.sha256(archive.read_bytes()).hexdigest()
    with tarfile.open(archive) as tar:
        tar.extractall(sources, filter='data')
source = sources / 'busybox'
shutil.copy2(previous / 'src/time.c', source / 'libbb/time.c')
shutil.copy2(previous / 'build/sources/busybox/.config', source / '.config')
wrappers = build / 'wrappers'
wrappers.mkdir()
prefix = str(wrappers / 'aarch64-linux-gnu-')
for name in ('gcc', 'ar', 'as', 'ld', 'nm', 'objcopy', 'objdump', 'ranlib', 'strip'):
    dest = Path(prefix + name)
    if name == 'gcc':
        dest.write_text('#!/bin/sh\nexec ' + target['cc'] + ' "$@"\n')
        dest.chmod(0o755)
    else:
        dest.symlink_to(target['tools'] + name)

# Keep vendor features; drop only ARM32 instruction-set flags and forced macros.
flags = ['-fPIC', '-O2', '-DHND_ROUTER', '-DRTCONFIG_HND_ROUTER_BE_4916',
         '-DCONFIG_BCMWL5', '-DSECURITY_NOTIFY', '-DBWDPI_LOGWAR',
         '-I' + str(sources / 'hdrs'), '-fstack-protector-strong', '-D_FORTIFY_SOURCE=2']
common = ['ARCH=aarch64', 'CROSS_COMPILE=' + prefix, 'CC=' + prefix + 'gcc']
env = os.environ.copy()
env.pop('LD_LIBRARY_PATH', None)
commands = [
    ['make', 'oldconfig', *common],
    ['make', '-j12', *common, 'SKIP_STRIP=y', 'EXTRA_CFLAGS=' + ' '.join(flags),
     'EXTRA_LDFLAGS=-Wl,--build-id=sha1 -Wl,-z,relro,-z,now', 'EXTRA_LDLIBS='],
    ['make', 'busybox.links', *common],
]
with (evidence / 'build.log').open('w') as log:
    for i, cmd in enumerate(commands):
        print('RUN:', cmd, file=log, flush=True)
        subprocess.run(cmd, cwd=source, env=env, input='\n'*2000 if i == 0 else None,
                       text=True, stdout=log, stderr=subprocess.STDOUT, check=True)
binary = build / 'busybox-aarch64'
shutil.copy2(source / 'busybox', binary)
subprocess.run([prefix + 'strip', '--strip-unneeded', str(binary)], env=env, check=True)
receipt = {'target': target, 'flags': flags, 'commands': commands, 'inputs': inputs,
           'sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
           'bytes': binary.stat().st_size,
           'removed_link_inputs': 'ARM32 vendorlib directory and unused libptcsrv',
           'firmware_deployed': False}
(evidence / 'build.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt, indent=2))
