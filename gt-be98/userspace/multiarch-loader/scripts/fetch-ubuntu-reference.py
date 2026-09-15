#!/usr/bin/env python3
"""Inspect authenticated Ubuntu packages in a workspace; never install on host."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import subprocess
import urllib.request

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--previous-checkpoint', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
old = a.previous_checkpoint.resolve(strict=True)
out = a.output.resolve()
cache = out / 'downloads'
cache.mkdir(parents=True, exist_ok=True)
policy = json.loads((old / 'configs/ubuntu-toolchain.json').read_text())
base = 'https://ports.ubuntu.com/ubuntu-ports/'
records = []

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def fetch(url, size, digest, name):
    path = cache / name
    assert not path.is_symlink()
    if not path.exists():
        previous = old / 'downloads' / name
        if previous.is_file() and sha(previous) == digest:
            shutil.copy2(previous, path)
        else:
            partial = path.with_name(path.name + '.part')
            with urllib.request.urlopen(url, timeout=45) as response, partial.open('wb') as target:
                shutil.copyfileobj(response, target)
            partial.rename(path)
    assert path.stat().st_size == int(size) and sha(path) == digest, name
    records.append({'url': url, 'cache_name': name, 'bytes': int(size), 'sha256': digest})
    return path

def paragraphs(text):
    for paragraph in text.split('\n\n'):
        result = {}
        key = None
        for line in paragraph.splitlines():
            if line[:1].isspace() and key:
                result[key] += '\n' + line.strip()
            elif ': ' in line or line.endswith(':'):
                key, value = line.split(':', 1)
                result[key] = value.strip()
        if result:
            yield result

release = policy['release']
signed = fetch(release['url'], release['bytes'], release['sha256'], release['cache_name'])
verification = subprocess.run(['gpgv', '--status-fd', '1', '--keyring',
                              '/usr/share/keyrings/ubuntu-archive-keyring.gpg', str(signed)],
                             check=True, capture_output=True, text=True)
assert '[GNUPG:] VALIDSIG ' + policy['signing_fingerprint'] + ' ' in verification.stdout
hashes = {}
in_hashes = False
for line in signed.read_text().splitlines():
    if line == 'SHA256:':
        in_hashes = True
    elif in_hashes and line.startswith(' '):
        digest, size, name = line.split()
        hashes[name] = (int(size), digest)
    elif in_hashes:
        in_hashes = False

def index(name):
    size, digest = hashes[name]
    filename = 'resolute-' + name.replace('/', '-')
    # Retain the names of the already-verified previous binary indices.
    filename = filename.replace('binary-arm64-', 'arm64-')
    path = fetch(base + 'dists/resolute/' + name, size, digest, filename)
    return list(paragraphs(lzma.decompress(path.read_bytes()).decode()))

arm64 = index('main/binary-arm64/Packages.xz') + index('universe/binary-arm64/Packages.xz')
armhf = index('main/binary-armhf/Packages.xz')
sources = index('main/source/Sources.xz')
available = {x['Package']: x for x in arm64 if 'Filename' in x}
selected = []
for arch, listing in [('arm64', arm64), ('armhf', armhf)]:
    for package in ['libc6', 'libc6-dev']:
        row = next(x for x in listing if x.get('Package') == package)
        selected.append((row, 'reference/' + arch))
for package in ['libc6-armel-cross', 'libc6-dev-armel-cross']:
    selected.append((available[package], 'reference/armel-cross'))

# The previous GCC 15 toolchain's package closure, translated to Ubuntu's
# armhf target package names, supplies an isolated arm64-host cross compiler.
for previous in policy['packages']:
    name = previous['package'].replace('arm-linux-gnueabi', 'arm-linux-gnueabihf')
    name = name.replace('-armel-cross', '-armhf-cross').replace('-cross-base-ports', '-cross-base')
    selected.append((available[name], 'toolchain-armhf'))

packages = []
for row, directory in selected:
    archive = fetch(base + row['Filename'], row['Size'], row['SHA256'], Path(row['Filename']).name)
    dest = out / directory
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(['dpkg-deb', '-x', str(archive), str(dest)], check=True)
    control = out / 'reference-control' / archive.stem
    if not control.exists():
        control.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['dpkg-deb', '-e', str(archive), str(control)], check=True)
    packages.append({'package': row['Package'], 'version': row['Version'],
                     'architecture': row['Architecture'], 'destination': directory,
                     'sha256': row['SHA256'], 'filename': row['Filename']})

source = next(x for x in sources if x.get('Package') == 'glibc')
for line in source['Checksums-Sha256'].splitlines():
    if not line.strip():
        continue
    digest, size, name = line.split()
    if not (name.endswith('.debian.tar.xz') or name.endswith('.dsc')):
        continue
    archive = fetch(base + source['Directory'] + '/' + name, size, digest, name)
    if name.endswith('.debian.tar.xz'):
        dest = out / 'ubuntu-glibc-packaging'
        dest.mkdir(exist_ok=True)
        subprocess.run(['tar', '-xf', str(archive), '-C', str(dest)], check=True)

result = {'signing_fingerprint': policy['signing_fingerprint'], 'signature_verified': True,
          'glibc_source_version': source['Version'], 'downloads': records, 'packages': packages,
          'host_packages_installed': False}
(out / 'evidence/ubuntu-reference.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'signature_verified': True, 'packages_extracted': len(packages),
                  'glibc_source_version': source['Version']}, indent=2))
