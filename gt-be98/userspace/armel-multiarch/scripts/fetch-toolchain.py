#!/usr/bin/env python3
"""Extract a pinned, signed Ubuntu arm64-host / armel-target GCC 15 toolchain."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re
import subprocess
import urllib.request

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--cache', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--keyring', type=Path, default=Path('/usr/share/keyrings/ubuntu-archive-keyring.gpg'))
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
policy = json.loads((root/'configs/ubuntu-toolchain.json').read_text())
if a.output.exists() or a.output.is_symlink():
    p.error('output must be a new directory; no host package installation')
a.cache.mkdir(parents=True, exist_ok=True)

def acquire(item):
    target = a.cache/item['cache_name']
    if target.is_symlink():
        raise ValueError('cache entry must be a regular file')
    if not target.exists():
        partial = target.with_suffix(target.suffix+'.part')
        with urllib.request.urlopen(item['url'], timeout=60) as response, partial.open('wb') as stream:
            while block := response.read(1024*1024):
                stream.write(block)
        partial.rename(target)
    if target.stat().st_size != item['bytes'] or digest(target) != item['sha256']:
        raise ValueError('download hash/size mismatch: '+target.name)
    return target

release = acquire(policy['release'])
verified = subprocess.run(['gpgv', '--status-fd', '1', '--keyring', str(a.keyring), str(release)],
                          check=True, capture_output=True, text=True)
if '[GNUPG:] VALIDSIG '+policy['signing_fingerprint']+' ' not in verified.stdout:
    raise ValueError('unexpected Ubuntu archive signing key')
signed_hashes = {}
in_sha256 = False
for line in release.read_text().splitlines():
    if line == 'SHA256:':
        in_sha256 = True
    elif in_sha256 and line.startswith(' '):
        hashvalue, length, name = line.split()
        signed_hashes[name] = (hashvalue, int(length))
    elif in_sha256:
        in_sha256 = False
available = {}
for item in policy['indices']:
    index = acquire(item)
    assert signed_hashes[item['release_path']] == (item['sha256'], item['bytes'])
    for stanza in lzma.decompress(index.read_bytes()).decode().split('\n\n'):
        fields = dict(re.findall(r'^([^\s:]+): (.*)$', stanza, re.M))
        if 'Filename' in fields:
            available[fields['Filename']] = fields
archives = []
for item in policy['packages']:
    signed = available[item['filename']]
    assert (signed['Package'], signed['Version'], signed['SHA256'], int(signed['Size'])) == (
        item['package'], item['version'], item['sha256'], item['bytes'])
    archives.append(acquire(item))
# Only authenticated archives are extracted, into an isolated workspace prefix.
a.output.mkdir(parents=True)
for archive in archives:
    subprocess.run(['dpkg-deb', '-x', str(archive), str(a.output)], check=True)
print(json.dumps({'packages': len(archives), 'signature_verified': True,
                  'compiler': 'Ubuntu GCC 15.2 arm-linux-gnueabi', 'host': 'aarch64'}, indent=2))
