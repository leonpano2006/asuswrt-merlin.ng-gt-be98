#!/usr/bin/env python3
"""Provide util-linux mount/umount for systemd's required command-line interface."""
import json
import os
from pathlib import Path
import shutil
import subprocess

r = Path(__file__).resolve().parents[1]
build = r / 'build/util-linux'
build.mkdir(exist_ok=True)
env = dict(os.environ, LC_ALL='C', CC=str(r / 'build/cc'),
    CFLAGS='-Os -g -frecord-gcc-switches', LDFLAGS='-Wl,--build-id=sha1',
    PKG_CONFIG_SYSROOT_DIR=str(r / 'sdk'),
    PKG_CONFIG_LIBDIR=str(r / 'sdk/usr/lib/aarch64-linux-gnu/pkgconfig'), PKG_CONFIG_PATH='')
commands = [[str(r / 'sources/util-linux-2.42.2/configure'), '--prefix=/usr',
    '--libdir=/usr/lib/aarch64-linux-gnu', '--host=aarch64-linux-gnu', '--build=aarch64-build-linux-gnu',
    '--disable-all-programs', '--enable-libblkid', '--enable-libmount', '--enable-mount',
    '--disable-static', '--disable-nls', '--without-systemd', '--without-python',
    '--disable-libmount-udev-support'], ['make', '-j4', 'mount', 'umount']]
(r / 'evidence/mount-tool-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
for name, command in zip(('mount-tools-configure', 'mount-tools-build'), commands):
    print(name, flush=True)
    with (r / 'evidence' / (name + '.log')).open('w') as log:
        p = subprocess.run(command, cwd=build, env=env, stdout=log, stderr=subprocess.STDOUT)
    if p.returncode:
        print((r / 'evidence' / (name + '.log')).read_text()[-6000:], flush=True)
        raise SystemExit(p.returncode)
dest = r / 'overlay/usr/gnu/bin'
dest.mkdir(parents=True, exist_ok=True)
for name in ('mount', 'umount'):
    shutil.copy2(build / '.libs' / name, dest / name)
    subprocess.run(['aarch64-linux-gnu-strip', '--strip-unneeded', str(dest / name)], check=True)
print('UTIL_LINUX_MOUNT_TOOLS_BUILT', flush=True)
