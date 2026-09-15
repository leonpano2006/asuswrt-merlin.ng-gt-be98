#!/usr/bin/env python3
"""Build the armel ABI/library smoke probe against the four freshly built libraries."""
import argparse
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--toolchain', type=Path, required=True)
p.add_argument('--build', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
tc, build = a.toolchain.resolve(strict=True), a.build.resolve(strict=True)
if a.output.exists():
    p.error('output already exists')
env = dict(os.environ, PATH=str(tc/'usr/bin')+':'+os.environ['PATH'],
           LD_LIBRARY_PATH=str(tc/'usr/lib/aarch64-linux-gnu'))
cmd = [str(tc/'usr/bin/arm-linux-gnueabi-gcc-15'), '--sysroot='+str(tc),
       '-O2', '-mcpu=cortex-a53', '-mfpu=neon-fp-armv8', '-mfloat-abi=softfp',
       '-U_TIME_BITS', '-U_FILE_OFFSET_BITS', '-static-libgcc']
for sub in ('zlib', 'expat/lib', 'json-c', 'libcap-ng/src'):
    cmd.append('-I'+str(build/sub))
cmd += [str(Path(__file__).with_name('library-probe.c')),
        '-L'+str(build/'rebuilt'), '-Wl,-rpath-link,'+str(build/'rebuilt'),
        '-l:libz.so.1', '-l:libexpat.so.1.5.2', '-l:libjson-c.so.2.0.2',
        '-l:libcap-ng.so.0.0.0', '-ldl', '-o', str(a.output)]
subprocess.run(cmd, env=env, check=True)
