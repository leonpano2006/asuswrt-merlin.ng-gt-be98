#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent
workspace = root.parent
sysroot = workspace / 'a53-runtimes-20260916/sysroots/aarch64'
binary = root / 'build/busybox-aarch64'
loader = sysroot / 'lib/ld-linux-aarch64.so.1'
libpath = str(sysroot / 'lib/aarch64-linux-gnu') + ':' + str(sysroot / 'usr/lib/aarch64-linux-gnu')
base = [str(loader), '--library-path', libpath, str(binary)]
results = []


def run(args, expected=None, data=None):
    p = subprocess.run(base + args, input=data, text=True, capture_output=True, timeout=10)
    row = dict(args=args, status=p.returncode, stdout=p.stdout, stderr=p.stderr)
    results.append(row)
    if p.returncode or (expected is not None and p.stdout.strip() != expected):
        raise RuntimeError(row)
    return p.stdout


try:
    applets = run(['--list']).splitlines()
    oldlinks = workspace / 'ping-diagnosis-20260922/build/sources/busybox/busybox.links'
    old = sorted({Path(x).name for x in oldlinks.read_text().splitlines()})
    assert sorted(applets) == old
    run(['sh', '-c', 'v=hello; test "$v" = hello && printf "%s\\n" "$((2147483648 + 1))"'], '2147483649')
    run(['awk', 'BEGIN { print 3*7 }'], '21')
    run(['sed', 's/alpha/beta/'], 'beta', 'alpha\n')
    run(['sort', '-n'], '1\n2\n3', '3\n1\n2\n')
    run(['date', '-u', '-d', '@2147483648', '+%Y-%m-%dT%H:%M:%SZ'], '2038-01-19T03:14:08Z')
    with tempfile.TemporaryDirectory(dir=root / 'build') as td:
        f = Path(td) / 'sparse-test'
        with f.open('wb') as out:
            out.truncate(5 * 1024**3)
        assert str(5 * 1024**3) in run(['ls', '-ln', str(f)]).split()
        run(['cp', str(root / 'build/sources/busybox/.config'), td + '/config'])
        assert (Path(td) / 'config').read_bytes() == (root / 'build/sources/busybox/.config').read_bytes()
        run(['tar', '-cf', td + '/config.tar', '-C', td, 'config'])
        run(['tar', '-tf', td + '/config.tar'], 'config')
    run(['ps'])
    run(['df', '-k', str(root)])
    run(['mount'])
    p = subprocess.run([str(loader), '--library-path', libpath, '--list', str(binary)],
                       text=True, capture_output=True, check=True)
    (root / 'evidence/host-loader.txt').write_text(p.stdout + p.stderr)
    print('PASS: 157 identical applets; shell, text tools, 2038 date, 5GiB file size, file/archive and read-only process/filesystem checks.')
finally:
    (root / 'evidence/host-tests.json').write_text(json.dumps(results, indent=2) + '\n')

sizes = {}
for name, path in [('armel', workspace / 'ping-diagnosis-20260922/build/busybox-fixed'),
                   ('aarch64', binary)]:
    dest = root / 'build' / (name + '.zst')
    subprocess.run(['zstd', '--ultra', '-22', '-T1', '-q', '-f', str(path), '-o', str(dest)], check=True)
    sizes[name] = dict(bytes=path.stat().st_size, zstd22_bytes=dest.stat().st_size)
(root / 'evidence/sizes.json').write_text(json.dumps(sizes, indent=2) + '\n')
print(json.dumps(sizes, indent=2))
