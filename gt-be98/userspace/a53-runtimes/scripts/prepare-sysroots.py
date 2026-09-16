#!/usr/bin/env python3
"""Create isolated SDK sysroots from the exact glibc 2.44 staged installations."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
workspace = root.parent
loader = workspace / 'multiarch-loader-20260916'
records = {}
for abi, triplet, sdk in [('armel', 'arm-linux-gnueabi', 'arm32/arm-buildroot-linux-gnueabi'),
                          ('armhf', 'arm-linux-gnueabihf', 'arm32/arm-buildroot-linux-gnueabi'),
                          ('aarch64', 'aarch64-linux-gnu', 'arm64/aarch64-buildroot-linux-gnu')]:
    old = json.loads((loader / 'builds' / abi / 'configuration.json').read_text())
    source = loader / 'builds' / abi / 'stage'
    dest = root / 'sysroots' / abi
    assert not dest.exists()
    subprocess.run(['cp', '-a', '--reflink=auto', str(source), str(dest)], check=True)
    kernel = workspace / 'github-push-20260915/dependency-sdks' / sdk / 'sysroot/usr/include'
    for name in ('asm', 'asm-generic', 'linux', 'mtd', 'rdma', 'scsi', 'sound', 'video', 'xen', 'drm', 'misc'):
        if (kernel / name).is_dir():
            shutil.copytree(kernel / name, dest / 'usr/include' / name, dirs_exist_ok=True)
    (dest / 'include').symlink_to('usr/include')
    (dest / 'usr' / triplet).mkdir(exist_ok=True)
    (dest / 'usr' / triplet / 'lib').symlink_to('../lib/' + triplet)
    if abi == 'aarch64':
        flags = ['-mcpu=cortex-a53+crc+crypto']
        driver = shlex.split(old['cc'])
        cxx = shlex.split(old['cxx'])
        driver = [x for x in driver if not x.startswith('--sysroot=')]
        cxx = [x for x in cxx if not x.startswith('--sysroot=')]
        hostlib = None
        tools = '/usr/bin/aarch64-linux-gnu-'
    else:
        flags = ['-mcpu=cortex-a53+crypto', '-march=armv8-a+crc+crypto',
                 '-mfpu=crypto-neon-fp-armv8', '-mfloat-abi=' + ('softfp' if abi == 'armel' else 'hard')]
        driver = [shlex.split(old['cc'])[0]]
        cxx = [shlex.split(old['cxx'])[0]]
        hostlib = old['host_library_dir']
        tools = str(Path(driver[0]).parent / (triplet + '-'))
    common = flags + ['--sysroot=' + str(dest), '-B' + str(dest / 'usr/lib' / triplet) + '/',
                      '-isystem', str(dest / 'usr/include'), '-L' + str(dest / 'usr/lib' / triplet),
                      '-Wl,-rpath-link,' + str(dest / 'lib' / triplet)]
    wrapperdir = root / 'builds' / abi / 'wrappers'
    wrapperdir.mkdir(parents=True)
    wrappers = {}
    for name, compiler in [('cc', driver), ('cxx', cxx)]:
        path = wrapperdir / name
        path.write_text('#!/bin/sh\nexec ' + shlex.join(compiler + common) + ' "$@"\n')
        path.chmod(0o755)
        wrappers[name] = str(path)
    env = dict(os.environ)
    if hostlib:
        env['LD_LIBRARY_PATH'] = hostlib
    macros = subprocess.check_output([wrappers['cc'], '-dM', '-E', '-x', 'c', '-'],
                                      input='#include <features.h>\n', env=env, text=True)
    for macro in ['__ARM_FEATURE_CRC32', '__ARM_FEATURE_CRYPTO']:
        assert '#define ' + macro + ' 1' in macros, (abi, macro)
    if abi != 'aarch64':
        assert '#define __ARM_FEATURE_IDIV 1' in macros
    assert '#define __GLIBC__ 2' in macros and '#define __GLIBC_MINOR__ 44' in macros
    version = subprocess.check_output([wrappers['cc'], '-dumpfullversion'], env=env, text=True).strip()
    record = dict(abi=abi, triplet=triplet, sysroot=str(dest), flags=flags,
                  cc=wrappers['cc'], cxx=wrappers['cxx'], host_library_dir=hostlib,
                  tools=tools, compiler_version=version, glibc='2.44',
                  glibc_source_commit=old['source_commit'])
    (root / 'builds' / abi / 'configuration.json').write_text(json.dumps(record, indent=2) + '\n')
    (root / 'evidence' / (abi + '-compiler-macros.txt')).write_text(macros)
    records[abi] = record
    print('Prepared glibc 2.44 sysroot and verified target features:', abi, flush=True)
(root / 'configs/build-targets.json').write_text(json.dumps(records, indent=2) + '\n')
