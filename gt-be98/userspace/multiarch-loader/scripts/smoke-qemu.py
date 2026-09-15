#!/usr/bin/env python3
"""Compile against staged glibc headers/libs and execute each ABI under QEMU."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shlex
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--work', type=Path, required=True)
args = p.parse_args()
r = args.work.resolve()
(r / 'evidence').mkdir(parents=True, exist_ok=True)
if not (r / 'tests/libc-smoke.c').is_file():
    p.error('copy tests/libc-smoke.c into the work directory first')
records = []
for abi in ['aarch64', 'armel', 'armhf']:
    cfg = json.loads((r / 'builds' / abi / 'configuration.json').read_text())
    stage = r / 'builds' / abi / 'stage'
    paths = {key: stage / cfg['configuration'][key].lstrip('/')
             for key in ['slibdir', 'rtlddir', 'libdir']}
    loader = {'aarch64': 'ld-linux-aarch64.so.1', 'armel': 'ld-linux.so.3',
              'armhf': 'ld-linux-armhf.so.3'}[abi]
    env = dict(os.environ)
    if cfg.get('host_library_dir'):
        env['LD_LIBRARY_PATH'] = cfg['host_library_dir']
    binary = r / 'tests' / ('libc-smoke-' + abi)
    cmd = shlex.split(cfg['cc']) + ['--sysroot=' + str(stage)] + cfg['flags'] + [
        '-fno-builtin', '-I' + str(stage / 'usr/include'),
        '-isystem', cfg['headers'], '-B' + str(paths['libdir']) + '/',
        str(r / 'tests/libc-smoke.c'), '-L' + str(paths['libdir']),
        '-L' + str(paths['slibdir']), '-Wl,-rpath-link,' + str(paths['slibdir']),
        '-pthread', '-lm', '-ldl', '-o', str(binary)]
    subprocess.run(cmd, env=env, check=True)
    env.pop('LD_LIBRARY_PATH', None)
    env['GCONV_PATH'] = str(paths['libdir'] / 'gconv')
    emulator, cpu = ('qemu-aarch64', 'cortex-a53') if abi == 'aarch64' else ('qemu-arm', 'max')
    command = [emulator, '-cpu', cpu, str(paths['rtlddir'] / loader),
               '--library-path', str(paths['slibdir']), str(binary)]
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=90)
    log = result.stdout + result.stderr
    (r / 'evidence' / ('smoke-' + abi + '-qemu.log')).write_text(log)
    print(abi, result.returncode, log, flush=True)
    if result.returncode or 'GLIBC_B53_SMOKE_COMPLETE' not in result.stdout:
        raise SystemExit('smoke failed for ' + abi)
    records.append({'abi': abi, 'emulator': emulator, 'cpu': cpu,
                    'returncode': result.returncode, 'output': result.stdout.splitlines(),
                    'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest()})
(r / 'evidence/qemu-smoke.json').write_text(json.dumps(records, indent=2) + '\n')
