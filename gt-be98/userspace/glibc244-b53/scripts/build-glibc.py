#!/usr/bin/env python3
"""Build glibc 2.44 for the three GT-BE98 ABIs in separate output trees."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

PIN = '2d5421ffca8893534d5e02ad38c28acd8e778fa3'
CPU_ALIASES = {'b53': 'cortex-a53', 'brahma-b53': 'cortex-a53',
               'cortex-a53': 'cortex-a53'}
ABIS = {
    'aarch64': {'host': 'aarch64-unknown-linux-gnu',
                'cpu_flags': ['-mcpu=cortex-a53+crypto+crc'],
                'slibdir': '/lib/aarch64-linux-gnu', 'rtlddir': '/lib',
                'libdir': '/usr/lib/aarch64-linux-gnu'},
    'armel': {'host': 'arm-linux-gnueabi',
              'cpu_flags': ['-mcpu=cortex-a53', '-mfpu=crypto-neon-fp-armv8',
                            '-mfloat-abi=softfp'],
              'slibdir': '/lib', 'rtlddir': '/lib', 'libdir': '/usr/lib'},
    'armhf': {'host': 'arm-linux-gnueabihf',
              'cpu_flags': ['-mcpu=cortex-a53', '-mfpu=crypto-neon-fp-armv8',
                            '-mfloat-abi=hard'],
              'slibdir': '/lib/arm-linux-gnueabihf',
              'rtlddir': '/lib/arm-linux-gnueabihf',
              'libdir': '/usr/lib/arm-linux-gnueabihf'},
}

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--abi', choices=ABIS, required=True)
p.add_argument('--cpu', choices=CPU_ALIASES, default='b53')
p.add_argument('--cc', required=True, help='Compiler command, including optional SDK arguments')
p.add_argument('--cxx', required=True)
p.add_argument('--headers', type=Path, required=True)
p.add_argument('--host-library-dir', type=Path,
               help='Optional native host libraries for a relocated compiler/binutils package')
p.add_argument('--jobs', type=int, default=6)
args = p.parse_args()
if os.uname().machine != 'aarch64' or not 1 <= args.jobs <= 12:
    p.error('use an AArch64 host and 1..12 jobs')
source, output, headers = (x.resolve() for x in [args.source, args.output, args.headers])
if source == output or source in output.parents:
    p.error('output must be outside the source tree')
sha = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
if sha != PIN or '#define VERSION "2.44"' not in (source / 'version.h').read_text():
    p.error('source must be the pinned, deployed glibc 2.44 revision')
if subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '-uno'], text=True):
    p.error('tracked glibc sources must be clean')
abi = ABIS[args.abi]
flags = ['-O2', '-g', *abi['cpu_flags']]
cc = shlex.split(args.cc)
version = subprocess.check_output(cc + ['-dumpfullversion'], text=True).strip()
if tuple(int(n) for n in version.split('.')[:2]) < (12, 1):
    p.error('glibc 2.44 requires GCC >= 12.1')
if not (headers / 'linux/version.h').is_file():
    p.error('provide exported Linux UAPI headers')
record = {'source_commit': sha, 'glibc': '2.44', 'abi': args.abi,
          'cpu_requested': args.cpu, 'cpu_resolved': CPU_ALIASES[args.cpu],
          'flags': flags, 'cc': args.cc, 'cxx': args.cxx,
          'compiler_version': version, 'headers': str(headers),
          'kernel_header_version_sha256': hashlib.sha256((headers / 'linux/version.h').read_bytes()).hexdigest(),
          'configuration': abi, 'minimum_kernel': '4.19'}
if args.host_library_dir:
    record['host_library_dir'] = str(args.host_library_dir.resolve())
output.mkdir(parents=True, exist_ok=True)
build, stage = output / 'build', output / 'stage'
build.mkdir(exist_ok=True)
manifest = output / 'configuration.json'
if manifest.exists() and json.loads(manifest.read_text()) != record:
    p.error('existing output uses different inputs; choose a new output directory')
manifest.write_text(json.dumps(record, indent=2) + '\n')
(build / 'configparms').write_text(''.join(f'{k}={abi[k]}\n' for k in ['slibdir', 'rtlddir', 'libdir']))
env = dict(os.environ)
for key in ['LD_PRELOAD', 'LD_LIBRARY_PATH', 'LIBRARY_PATH', 'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH']:
    env.pop(key, None)
env.update(CC=args.cc, CXX=args.cxx, CFLAGS=shlex.join(flags),
           CXXFLAGS=shlex.join(flags), CPPFLAGS='', LDFLAGS='', LC_ALL='C')
env['PATH'] = str(Path(cc[0]).resolve().parent) + os.pathsep + env['PATH']
if args.host_library_dir:
    env['LD_LIBRARY_PATH'] = str(args.host_library_dir.resolve())
configure = [str(source / 'configure'), '--prefix=/usr',
             '--build=aarch64-linux-gnu', '--host=' + abi['host'],
             '--enable-kernel=4.19', '--disable-werror', '--with-headers=' + str(headers)]
if args.abi != 'aarch64':
    configure.append('--disable-nscd')
steps = [('configure', configure), ('make', ['make', '-j' + str(args.jobs)]),
         ('install', ['make', 'install', 'DESTDIR=' + str(stage)])]
results = []
for name, command in steps:
    if name == 'configure' and (build / 'Makefile').is_file():
        continue
    start = time.monotonic()
    log = output / (name + '.log')
    with log.open('wb') as stream:
        result = subprocess.run(command, cwd=build, env=env, stdout=stream, stderr=subprocess.STDOUT)
    item = {'step': name, 'returncode': result.returncode,
            'elapsed_seconds': round(time.monotonic() - start, 2),
            'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()}
    results.append(item)
    (output / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(item), flush=True)
    if result.returncode:
        print('\n'.join(log.read_text(errors='replace').splitlines()[-35:]))
        raise SystemExit(result.returncode)
print('GLIBC_STAGED ' + str(stage), flush=True)
