#!/usr/bin/env python3
"""Isolate the existing native AArch64 compiler/glibc and exact router dependencies."""
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess

r = Path(__file__).resolve().parents[1]
w = r.parent
sdk = r / 'sdk'
assert not sdk.exists()
subprocess.run(['cp', '-a', '--reflink=auto', str(w / 'a53-runtimes-20260916/sysroots/aarch64'), str(sdk)], check=True)
lib = sdk / 'usr/lib/aarch64-linux-gnu'
rootfs = w / 'rootfs-no-adsl-20260916/build/unpacked-rootfs'
record = {}
for name in ('libmount.so.1.1.0', 'libblkid.so.1.1.0', 'libgcc_s.so.1'):
    p = rootfs / 'usr/lib/aarch64-linux-gnu' / name
    shutil.copy2(p, lib / name)
    record[name] = hashlib.sha256(p.read_bytes()).hexdigest()
for name, target in [('libmount.so', 'libmount.so.1.1.0'), ('libmount.so.1', 'libmount.so.1.1.0'),
                     ('libblkid.so', 'libblkid.so.1.1.0'), ('libblkid.so.1', 'libblkid.so.1.1.0'),
                     ('libgcc_s.so', 'libgcc_s.so.1')]:
    (lib / name).symlink_to(target)
util = r / 'sources/util-linux-2.42.2'
for component in ('mount', 'blkid'):
    prefix = 'LIB' + component.upper()
    source = util / ('lib' + component) / 'src' / ('lib' + component + '.h.in' if component == 'mount' else 'blkid.h.in')
    text = source.read_text()
    values = {'VERSION': '2.42.2', 'MAJOR_VERSION': '2', 'MINOR_VERSION': '42', 'PATCH_VERSION': '2', 'DATE': '16-Jun-2026'}
    for key, value in values.items():
        text = text.replace('@' + prefix + '_' + key + '@', value)
    assert not re.search(r'@[A-Z_]+@', text)
    folder = sdk / 'usr/include' / ('libmount' if component == 'mount' else 'blkid')
    folder.mkdir(exist_ok=True)
    (folder / ('libmount.h' if component == 'mount' else 'blkid.h')).write_text(text)
    pcdir = lib / 'pkgconfig'
    pcdir.mkdir(exist_ok=True)
    (pcdir / (component + '.pc')).write_text(
        'prefix=/usr\nlibdir=${prefix}/lib/aarch64-linux-gnu\nincludedir=${prefix}/include\n'
        f'Name: {component}\nDescription: Existing GT-BE98 {component} runtime\nVersion: 2.42.2\n'
        f'Libs: -L${{libdir}} -l{component}\nCflags: -I${{includedir}}/{folder.name}\n')
gcc = w / 'gcc162-usb/obj/gcc'
libgcc = w / 'a53-runtimes-20260916/builds/aarch64/gcc-runtime/aarch64-linux-gnu/libgcc'
compiler = [str(gcc / 'xgcc'), '-B' + str(gcc) + '/', '-B' + str(libgcc) + '/',
            '-mcpu=cortex-a53+crc+crypto', '--sysroot=' + str(sdk), '-B' + str(lib) + '/',
            '-isystem', str(sdk / 'usr/include'), '-L' + str(lib),
            '-Wl,-rpath-link,' + str(lib), '-Wl,-rpath-link,' + str(sdk / 'lib/aarch64-linux-gnu')]
wrapper = r / 'build/cc'
wrapper.write_text('#!/bin/sh\nexec ' + shlex.join(compiler) + ' "$@"\n')
wrapper.chmod(0o755)
loader = sdk / 'lib/ld-linux-aarch64.so.1'
runner = r / 'build/run-target'
runner.write_text('#!/bin/sh\nexec ' + shlex.join([str(loader), '--library-path', str(lib) + ':' + str(sdk / 'lib/aarch64-linux-gnu')]) + ' "$@"\n')
runner.chmod(0o755)
version = subprocess.check_output([str(wrapper), '-dumpfullversion'], text=True).strip()
assert version == '16.2.0'
macros = subprocess.check_output([str(wrapper), '-dM', '-E', '-x', 'c', '-'], input='#include <features.h>\n', text=True)
for feature in ('__ARM_FEATURE_CRC32', '__ARM_FEATURE_CRYPTO'):
    assert '#define ' + feature + ' 1' in macros
assert '#define __GLIBC_MINOR__ 44' in macros
(r / 'evidence/compiler-macros.txt').write_text(macros)
(r / 'evidence/sdk.json').write_text(json.dumps({'native_host': 'aarch64', 'compiler_version': version,
    'glibc': '2.44', 'cpu': 'cortex-a53+crc+crypto', 'compiler': compiler,
    'existing_router_libraries': record, 'new_sysroot_only': True}, indent=2) + '\n')
print('Prepared isolated native AArch64 GCC 16.2.0 / glibc 2.44 SDK')
