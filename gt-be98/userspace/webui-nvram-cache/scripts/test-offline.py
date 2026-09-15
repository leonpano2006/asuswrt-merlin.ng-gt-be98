#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--sdk-prefix', required=True)
parser.add_argument('--rootfs', type=Path, required=True)
args = parser.parse_args()
base = Path(__file__).resolve().parent.parent
build = base / 'build'
build.mkdir(exist_ok=True)
run = lambda cmd: subprocess.run(cmd, check=True)
run([args.sdk_prefix+'gcc', '-O0', '-g', '-Wall', '-Wextra', '-rdynamic',
     str(base/'scripts/nvram-cache-repro.c'), '-ldl', '-o', str(build/'nvram-cache-repro')])
run([args.sdk_prefix+'as', str(base/'scripts/cache-get-refresh.S'), '-o', str(build/'cache-get-refresh.o')])
run([args.sdk_prefix+'ld', '-Ttext=0x7810', '-e', 'cache_get_refresh',
     '--defsym=cache_update=0x5064', '--defsym=cache_find=0x4bc8',
     '--defsym=get_unlock=0x568c', '--defsym=get_mark_referenced=0x56b0',
     str(build/'cache-get-refresh.o'), '-o', str(build/'cache-get-refresh.elf')])
run([args.sdk_prefix+'objcopy', '-O', 'binary', '-j', '.text',
     str(build/'cache-get-refresh.elf'), str(build/'cache-get-refresh.bin')])
manifest = json.loads((build/'libnvram.manifest.json').read_text())
assert (build/'cache-get-refresh.bin').read_bytes().hex() == manifest['trampoline_hex']
command = ['qemu-arm', '-L', str(args.rootfs), str(args.rootfs/'usr/lib/ld-linux.so.3'),
           '--library-path', str(args.rootfs/'usr/lib'), str(build/'nvram-cache-repro')]
records = []
for variant, path, cases in [
    ('original', args.rootfs/'usr/lib/libnvram.so', ['remove']),
    ('fixed', build/'libnvram.so', ['remove', 'remove-held', 'grow', 'empty', 'stable', 'absent'])]:
    for case in cases:
        r = subprocess.run(command+[str(path), case], capture_output=True, text=True)
        records.append({'variant': variant, 'case': case, 'exit': r.returncode,
                        'stdout': r.stdout, 'stderr': r.stderr})
        assert r.returncode == (1 if variant == 'original' else 0), records[-1]
result = {'assembler_matches_patch': True, 'cases': records}
(base/'evidence').mkdir(exist_ok=True)
(base/'evidence/offline-tests.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
