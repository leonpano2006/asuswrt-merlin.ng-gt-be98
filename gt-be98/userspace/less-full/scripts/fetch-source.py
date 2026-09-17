#!/usr/bin/env python3
"""Fetch the pinned stable release and verify its published package signature."""
from pathlib import Path
import json
import subprocess
import tarfile
from common import sha

r = Path(__file__).resolve().parents[1]
record = json.loads((r / 'configs/build-inputs.json').read_text())
(r / 'sources').mkdir(exist_ok=True)
(r / 'evidence').mkdir(exist_ok=True)
(r / 'stage').mkdir(exist_ok=True)
(r / 'candidate').mkdir(exist_ok=True)
for name in ('less-704.tar.gz', 'less-704.sig', 'pubkey.asc'):
    file = r / 'sources' / name
    if not file.exists():
        subprocess.run(['curl', '-fL', '--retry', '2', '-o', str(file),
                        'https://greenwoodsoftware.com/less/' + name], check=True)
archive = r / 'sources/less-704.tar.gz'
assert sha(archive) == record['sha256']
keyring = r / 'build/gnupg'
keyring.mkdir(mode=0o700, parents=True, exist_ok=True)
gpg = ['gpg', '--homedir', str(keyring)]
subprocess.run(gpg + ['--import', str(r / 'sources/pubkey.asc')], check=True)
result = subprocess.run(gpg + ['--status-fd', '1', '--verify',
    str(r / 'sources/less-704.sig'), str(archive)], stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT, text=True, check=True)
assert '[GNUPG:] VALIDSIG ' + record['signer'] + ' ' in result.stdout
(r / 'evidence/source-signature.txt').write_text(result.stdout)
assert not (r / 'sources/less-704').exists()
with tarfile.open(archive) as tar:
    tar.extractall(r / 'sources', filter='data')
