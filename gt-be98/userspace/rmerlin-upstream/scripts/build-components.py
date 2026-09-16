#!/usr/bin/env python3
"""Rebuild open management sources; retain exact GT-BE98 blob inputs and TLS ABI."""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import json
import os
import shlex
import shutil
import subprocess

r = Path(__file__).resolve().parents[1]
w = r.parent
router = r / 'source-tree/release/src/router'
old = w / 'leon-cgroup-20260915/archive/worktree/release/src/router'
parent_root = w / 'systemd-service-split-20260916/build/production-rootfs'
parent_lib = parent_root / 'usr/lib/arm-linux-gnueabi'
stage = r / 'build/management-libs'
stage.mkdir(exist_ok=True)
t = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env = dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir'])
parser = argparse.ArgumentParser()
parser.add_argument('components', nargs='*', default=['shared', 'libovpn', 'rc', 'httpd', 'infosvr'])
parser.add_argument('--link-only', action='store_true')
args = parser.parse_args()

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def flags_for(rows):
    result = []
    for flag in rows['CFLAGS']:
        if flag.startswith(('-march=', '-mcpu=', '-mfpu=', '-mfloat-abi=', '-D__ARM_ARCH_7A__', '-I/opt/', '-L/opt/')):
            continue
        # These management processes share objects with vendor libraries, so
        # use 1.1 headers and libraries throughout their dependency boundary.
        if flag.startswith('-I') and '/openssl' in flag:
            continue
        result.append(flag)
        if flag.startswith('-I' + str(router)):
            fallback = old / Path(flag[2:]).relative_to(router)
            if fallback.is_dir(): result.append('-I' + str(fallback))
    result += ['-I' + str(old / 'openssl-1.1/include'), '-std=gnu11', '-D_GNU_SOURCE',
               '-frecord-gcc-switches', '-fno-strict-aliasing',
               '-Wno-error=implicit-function-declaration', '-Wno-error=int-conversion',
               '-Wno-error=incompatible-pointer-types', '-Wno-error=implicit-int',
               '-Wno-error=return-mismatch', '-Wno-error=deprecated-declarations']
    return result

def library(flag):
    if flag.startswith('-l:'): name = flag[3:]
    else:
        base = flag[2:]
        name = {'dl': 'libdl.so.2', 'pthread': 'libpthread.so.0', 'crypt': 'libcrypt.so.1',
                'm': 'libm.so.6', 'rt': 'librt.so.1', 'gcc_s': 'libgcc_s.so.1'}.get(base, 'lib' + base + '.so')
    for directory in [stage, parent_lib]:
        path = directory / name
        if path.exists(): return '-l:' + path.name
    raise RuntimeError('Unresolved firmware link dependency: ' + flag)

def build(component):
    logtext = (r / 'evidence' / (component + '-flags.log')).read_text()
    rows = {line.split('=', 1)[0][5:]: shlex.split(line.split('=', 1)[1])
            for line in logtext.splitlines() if line.startswith('LEON_')}
    source = router / component
    out = r / 'build' / ('management-' + component)
    out.mkdir(exist_ok=True)
    vpath = [source]
    for line in logtext.splitlines():
        if line.startswith('vpath %.c '):
            vpath.extend(source / p for p in line[len('vpath %.c '):].split(':'))
    objects = list(dict.fromkeys(rows['OBJS']))
    if component == 'infosvr': objects = ['infosvr.o', 'common.o', 'packet.o', 'storage.o']
    special = {Path(x).name for x in rows.get('ID_OBJS', [])}
    flags = flags_for(rows)
    commands = []; inputs = []; jobs = []
    for name in objects:
        dest = out / Path(name).name
        leaf = Path(name).with_suffix('.c').name
        # These explicit vendor Makefile rules override the generic C rule.
        model_object = source / 'prebuild/GT-BE98' / Path(name).name
        prefer_model = (component == 'shared' and name in
                        ('bcmutils.o', 'bcmwifi_channels.o', 'bcmxtlv.o')
                        and model_object.is_file())
        candidates = [] if name.startswith('prebuild/') or prefer_model else [p / leaf for p in vpath]
        original = next((p for p in candidates if p.is_file()), None)
        if original:
            command = [t['cc']] + flags
            if Path(name).name in special: command += rows.get('ID_CFLAGS', [])
            command += ['-MMD', '-MF', str(dest.with_suffix('.d')), '-c', str(original), '-o', str(dest)]
            commands.append(command); jobs.append((name, command))
            inputs.append({'object': name, 'source': str(original), 'sha256': digest(original), 'prebuilt': False})
        else:
            choices = [source / 'prebuild/GT-BE98' / Path(name).name,
                       source / 'prebuilt/GT-BE98' / Path(name).name]
            for package in ['sw-hw-auth', 'aaews']:
                choices.append(router / package / 'prebuild/GT-BE98' / Path(name).name)
            original = next((p for p in choices if p.is_file()), None)
            assert original, (component, name, 'No selected source or exact model blob')
            shutil.copy2(original, dest)
            inputs.append({'object': name, 'source': str(original), 'sha256': digest(original), 'prebuilt': True})
    (out / 'compile-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    (out / 'inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
    def compile(job):
        name, command = job
        with (out / (Path(name).stem + '.log')).open('w') as log:
            result = subprocess.run(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT)
        return name, result.returncode
    if not args.link_only:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(compile, jobs))
        failed = [name for name, code in results if code]
        if failed:
            print(component, 'COMPILE_FAILED', failed, flush=True)
            for name in failed:
                lines = (out / (Path(name).stem + '.log')).read_text().splitlines()
                print(name, '\n'.join(x for x in lines if 'error:' in x)[:1300], flush=True)
            return False
    key = {'rc': 'LDFLAGS2', 'httpd': 'LIBS'}.get(component, 'LDFLAGS')
    recipe_flags = rows[key] + (rows.get('EXTRALDFLAGS', []) if component == 'httpd' else rows.get('EXTRA_LD_FLAGS', []) if component == 'shared' else [])
    libs = list(dict.fromkeys(library(x) for x in recipe_flags if x.startswith('-l')))
    soname = {'shared': 'libshared.so', 'libovpn': 'libovpn.so'}.get(component)
    output = out / (soname or component)
    cmd = [t['cc'], '-Wl,--build-id=sha1,-z,now', '-L' + str(stage),
           '-L' + str(parent_lib), '-o', str(output)]
    # Preserve linker policy from the authoritative component recipe, including
    # rc's removal of unreachable function/data sections.
    cmd += list(dict.fromkeys(x for x in recipe_flags if x.startswith('-Wl,')))
    if soname: cmd += ['-shared', '-Wl,-soname,' + soname]
    cmd += [str(out / Path(name).name) for name in objects]
    cmd += ['-Wl,--no-as-needed'] + libs + ['-Wl,-rpath-link,' + str(stage), '-Wl,-rpath-link,' + str(parent_lib)]
    if component == 'rc': cmd += ['-Wl,--wrap=kill,--wrap=reboot,--export-dynamic-symbol=leon_rc_is_manager']
    (out / 'link-command.json').write_text(json.dumps(cmd, indent=2) + '\n')
    with (out / 'link.log').open('w') as log:
        result = subprocess.run(cmd, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print(component, 'LINK_FAILED', (out / 'link.log').read_text()[-5000:], flush=True)
        return False
    if soname: shutil.copy2(output, stage / soname)
    record = {'component': component, 'output': str(output), 'sha256': digest(output),
              'compiled_sources': len(jobs), 'retained_model_objects': sum(x['prebuilt'] for x in inputs),
              'openssl_abi': 'legacy 1.1, isolated from new standalone 3.5 consumers', 'compiler': t}
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(component, 'BUILT', len(jobs), 'sources', record['retained_model_objects'], 'model blobs', flush=True)
    return True

for component in args.components:
    if not build(component): raise SystemExit(1)
