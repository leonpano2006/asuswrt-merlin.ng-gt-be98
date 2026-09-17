#!/usr/bin/env python3
"""Build upstream OpenSSL 4 independently of the ASUS ARM32 TLS closure."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

r = Path(__file__).resolve().parents[1]
w = r.parent
source = r / 'sources/openssl-4.0.2'
archive = r / 'sources/openssl-4.0.2.tar.gz'
expected = (r / 'sources/openssl-4.0.2.tar.gz.sha256').read_text().split()[0]
assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected
assert os.uname().machine == 'aarch64'
if not source.exists():
    with tarfile.open(archive) as t:
        t.extractall(r / 'sources', filter='data')
build = r / 'build/openssl4'
build.mkdir(parents=True, exist_ok=False)
sdk = r / 'sdk'
if not sdk.exists():
    subprocess.run(['cp', '-a', '--reflink=auto', str(w / 'systemd-upgrade-20260917/sdk'), str(sdk)], check=True)
for name in ['cc', 'run-target']:
    p = r / 'build' / name
    p.write_text((w / 'systemd-upgrade-20260917/build' / name).read_text().replace(
        str(w / 'systemd-upgrade-20260917/sdk'), str(sdk)))
    p.chmod(0o755)
env = dict(os.environ, CC=str(r / 'build/cc'), AR='/usr/bin/aarch64-linux-gnu-ar',
           RANLIB='/usr/bin/aarch64-linux-gnu-ranlib', LC_ALL='C')
env.pop('LD_LIBRARY_PATH', None)
commands = []
start = time.monotonic()
def run(command, label):
    commands.append({'cwd': str(build), 'argv': command})
    (r / 'evidence/openssl4-commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    print(label, flush=True)
    logpath = r / 'evidence' / (label + '.log')
    with logpath.open('w') as log:
        p = subprocess.run(command, cwd=build, env=env, stdout=log, stderr=subprocess.STDOUT)
    if p.returncode:
        print(logpath.read_text()[-6000:])
        raise SystemExit(p.returncode)

run(['perl', str(source / 'Configure'), 'linux-aarch64', '--prefix=/usr',
     '--openssldir=/usr/lib/ssl/openssl4', '--libdir=lib/aarch64-linux-gnu',
     'shared', '-O2', '-g', '-frecord-gcc-switches', '-fstack-protector-strong',
     '-Wl,--build-id=sha1,-z,relro,-z,now'], 'openssl4-configure')
run(['make', '-j8', 'build_sw'], 'openssl4-make')
run(['make', 'DESTDIR=' + str(r / 'build/openssl4-install'), 'install_sw'], 'openssl4-install')
files = {}
for name in ['libcrypto.so.4', 'libssl.so.4', 'apps/openssl', 'providers/legacy.so']:
    p = build / name
    files[name] = {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
record = {'source': 'OpenSSL 4.0.2 unmodified upstream', 'source_sha256': expected,
          'compiler': subprocess.check_output([str(r / 'build/cc'), '-dumpfullversion'], text=True).strip(),
          'glibc': '2.44', 'mcpu': 'cortex-a53+crc+crypto',
          'build_id': 'GNU sha1 (identifier, not a digital signature)',
          'elapsed_seconds': round(time.monotonic() - start, 2),
          'completed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'files': files, 'router_modified': False, 'tested': False}
(r / 'evidence/openssl4-build.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2), flush=True)
