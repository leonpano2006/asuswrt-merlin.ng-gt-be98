#!/usr/bin/env python3
"""Build runtime probes on DGX, including genuine GCC 10 legacy consumers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--loader-checkpoint', type=Path, required=True)
p.add_argument('--legacy-sdk', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
commands = []
for abi in ('armel', 'armhf', 'aarch64', 'armel-legacy'):
    target = 'armel' if abi == 'armel-legacy' else abi
    cfg = json.loads((a.loader_checkpoint / 'builds' / target / 'configuration.json').read_text())
    triplet = {'armel': 'arm-linux-gnueabi', 'armhf': 'arm-linux-gnueabihf',
               'aarch64': 'aarch64-linux-gnu'}[target]
    env = dict(os.environ)
    if cfg.get('host_library_dir'):
        env['LD_LIBRARY_PATH'] = cfg['host_library_dir']
    cc, cxx = shlex.split(cfg['cc']), shlex.split(cfg['cxx'])
    static = ['-static-libstdc++']
    library = root / 'packages/runtime/usr/lib' / triplet / 'libgcc_s.so.1'
    if abi == 'aarch64':
        cc, cxx, static = ['/usr/bin/gcc-13'], ['/usr/bin/g++-13'], []
    if abi == 'armel-legacy':
        prefix = a.legacy_sdk.resolve() / 'bin/arm-buildroot-linux-gnueabi-'
        cc, cxx, static = [str(prefix) + 'gcc'], [str(prefix) + 'g++'], []
        env.pop('LD_LIBRARY_PATH', None)
        assert subprocess.check_output(cc + ['-dumpfullversion'], env=env, text=True).strip() == '10.3.0'
        # A real legacy consumer must link against its original glibc 2.32 and
        # libgcc 10.3 SDK, then execute with the candidate's glibc 2.44/libgcc 15.
        # Linking the new runtime to the old SDK would require GLIBC_2.34 there.
        library = Path(subprocess.check_output(cc + ['-print-file-name=libgcc_s.so.1'],
                                              env=env, text=True).strip()).resolve(strict=True)
    link = root / 'tests/link' / abi
    link.mkdir(parents=True, exist_ok=True)
    entry = link / 'libgcc_s.so'
    if entry.is_symlink() or entry.is_file():
        entry.unlink()
    assert not entry.exists()
    # Preserve GCC's linker-script contract: arithmetic/atomic support can
    # come from libgcc.a while exception unwinding uses shared libgcc_s.so.1.
    # A bare .so symlink incorrectly drops the static fallback on ARMv5 builds.
    entry.write_text('GROUP ( "' + str(library) + '" -lgcc )\n')
    flags = cfg['configuration']['cpu_flags'] + [
        '-U_TIME_BITS', '-U_FILE_OFFSET_BITS', '-O2', '-g', '-fexceptions',
        '-funwind-tables', '-fno-omit-frame-pointer', '-fno-optimize-sibling-calls',
        '-L' + str(link), '-shared-libgcc']
    out = root / 'tests/bin'
    out.mkdir(exist_ok=True)
    definitions = [
        (cc, ['-std=gnu11', str(root / 'tests/runtime-smoke.c'), '-pthread', '-ldl',
              '-lgcc_s', '-o', str(out / ('runtime-' + abi))]),
        (cxx, ['-std=c++11', '-fPIC', '-shared', '-Wl,-z,defs'] + static + [
            str(root / 'tests/throw-library.cpp'), '-o', str(out / ('throw-' + abi + '.so'))]),
        # Export the main executable's C++ runtime so the test DSO shares its
        # exception state when libstdc++ is static. Otherwise both old and new
        # libgcc controls abort because two independent C++ runtimes are loaded.
        (cxx, ['-std=c++11', '-rdynamic'] + static + [str(root / 'tests/exception-smoke.cpp'),
            '-pthread', '-ldl', '-o', str(out / ('exception-' + abi))])]
    for compiler, args in definitions:
        command = compiler + flags + args
        subprocess.run(command, env=env, check=True)
        commands.append({'abi': abi, 'command': command,
                         'host_library_dir': env.get('LD_LIBRARY_PATH'),
                         'link_runtime_sha256': hashlib.sha256(library.read_bytes()).hexdigest()})
    print('Built probes for', abi, flush=True)
(root / 'evidence/probe-build-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
