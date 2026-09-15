#!/usr/bin/env python3
"""Compile offline guest probes on the AArch64 build host."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arm32-sdk', type=Path, required=True)
p.add_argument('--arm64-sdk', type=Path, required=True)
p.add_argument('--armhf-ubuntu-sysroot', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
src = Path(__file__).resolve().parent
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
arm32 = a.arm32_sdk.resolve() / 'bin/arm-buildroot-linux-gnueabi-gcc'
arm64 = a.arm64_sdk.resolve() / 'bin/aarch64-buildroot-linux-gnu-gcc'
ubuntu = a.armhf_ubuntu_sysroot.resolve()
armhf = ubuntu / 'usr/bin/arm-linux-gnueabihf-gcc'
records = []

def build(cc, source, name, flags=(), env=None):
    command = [str(cc), '-O2', '-Wall', '-Wextra', str(src / source), '-o', str(out / name), *flags]
    subprocess.run(command, env=env, check=True)
    records.append({'output': name, 'source': source,
                    'sha256': hashlib.sha256((out / name).read_bytes()).hexdigest(),
                    'source_sha256': hashlib.sha256((src / source).read_bytes()).hexdigest(),
                    'flags': [v.replace(str(out), '${PROBES}').replace(str(ubuntu), '${ARMHF_SYSROOT}') for v in flags],
                    'compiler': subprocess.check_output([str(cc), '-dumpmachine'], text=True, env=env).strip(),
                    'version': subprocess.check_output([str(cc), '-dumpfullversion'], text=True, env=env).strip()})

build(arm32, 'bootguard-provider.c', 'bootguard-provider.so', ['-shared', '-fPIC', '-Wl,-soname,bootguard-provider.so'])
build(arm32, 'guardcheck.c', 'guardcheck', ['-L' + str(out), '-Wl,--no-as-needed', '-l:bootguard-provider.so'])
build(arm32, 'identity-probe.c', 'identity-probe', ['-ldl'])
build(arm32, 'abi-probe.c', 'abi-probe-armel', ['-mcpu=cortex-a53', '-mfpu=crypto-neon-fp-armv8', '-mfloat-abi=softfp', '-pthread', '-lm'])
build(arm64, 'abi-probe.c', 'abi-probe-aarch64', ['-mcpu=cortex-a53', '-pthread', '-lm'])
env = dict(os.environ, PATH=str(ubuntu / 'usr/bin') + ':' + os.environ['PATH'],
           LD_LIBRARY_PATH=str(ubuntu / 'usr/lib/aarch64-linux-gnu'))
build(armhf, 'abi-probe.c', 'abi-probe-armhf', ['--sysroot=' + str(ubuntu), '-mcpu=cortex-a53', '-mfpu=crypto-neon-fp-armv8', '-mfloat-abi=hard', '-pthread', '-lm'], env)
(out / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')
print(json.dumps(records, indent=2))
