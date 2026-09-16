#!/usr/bin/env python3
"""Extract signed Ubuntu GCC 15 runtime packages without installing on the host."""
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import subprocess
import urllib.request

root = Path(__file__).resolve().parents[1]
config = json.loads((root / 'configs/ubuntu-source.json').read_text())
cache = root / 'downloads'
cache.mkdir(exist_ok=True)
release = cache / (config['suite'] + '-InRelease')

if not release.exists():
    snapshot = root / 'configs' / (config['suite'] + '-InRelease')
    if snapshot.is_file():
        shutil.copy2(snapshot, release)
    else:
        with urllib.request.urlopen(config['release_url'], timeout=45) as source:
            release.write_bytes(source.read())

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

assert sha(release) == config['release_sha256']
result = subprocess.run(['gpgv', '--status-fd', '1', '--keyring',
                         '/usr/share/keyrings/ubuntu-archive-keyring.gpg', str(release)],
                        check=True, capture_output=True, text=True)
assert '[GNUPG:] VALIDSIG ' + config['signing_fingerprint'] + ' ' in result.stdout
hashes = {}
active = False
for line in release.read_text().splitlines():
    if line == 'SHA256:':
        active = True
    elif active and line.startswith(' '):
        digest, size, name = line.split()
        hashes[name] = (int(size), digest)
    elif active:
        active = False

def fetch(url, size, digest, name):
    path = cache / name
    if not path.exists():
        partial = path.with_name(path.name + '.partial')
        with urllib.request.urlopen(url, timeout=45) as source, partial.open('wb') as dest:
            shutil.copyfileobj(source, dest)
        partial.rename(path)
    assert path.stat().st_size == int(size) and sha(path) == digest, name
    return path

def paragraphs(text):
    for block in text.split('\n\n'):
        row = {}
        key = None
        for line in block.splitlines():
            if line.startswith(' ') and key:
                row[key] += '\n' + line.strip()
            elif ':' in line:
                key, value = line.split(':', 1)
                row[key] = value.strip()
        if row:
            yield row

available = {}
indices = []
for component in ('main', 'universe'):
    name = component + '/binary-arm64/Packages.xz'
    size, digest = hashes[name]
    # Address the index by its authenticated digest, avoiding a mutable index
    # URL changing between the Release download and package resolution.
    index_url = (config['base'] + 'dists/' + config['suite'] + '/' + component
                 + '/binary-arm64/by-hash/SHA256/' + digest)
    path = fetch(index_url,
                 size, digest, config['suite'] + '-' + component + '-arm64-Packages.xz')
    available.update({row['Package']: row for row in paragraphs(lzma.decompress(path.read_bytes()).decode())})
    indices.append({'release_path': name, 'bytes': size, 'sha256': digest})
records = []
licenses = []
for abi in ('armel', 'armhf'):
    name = 'libgcc-s1-' + abi + '-cross'
    row = available[name]
    assert row['Version'].startswith('15.'), (name, row['Version'])
    assert row['Source'].startswith('gcc-15-cross'), row['Source']
    path = fetch(config['base'] + row['Filename'], row['Size'], row['SHA256'],
                 Path(row['Filename']).name)
    dest = root / 'extracted' / abi
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(['dpkg-deb', '-x', str(path), str(dest)], check=True)
    base_name = 'gcc-15-cross-base-ports' if abi == 'armel' else 'gcc-15-cross-base'
    base = available[base_name]
    assert base['Version'].startswith('15.')
    license_archive = fetch(config['base'] + base['Filename'], base['Size'],
                            base['SHA256'], Path(base['Filename']).name)
    subprocess.run(['dpkg-deb', '-x', str(license_archive), str(dest)], check=True)
    copyright_file = dest / 'usr/share/doc' / name / 'copyright'
    assert copyright_file.is_file()
    license_dir = root / 'licenses'
    license_dir.mkdir(exist_ok=True)
    shutil.copy2(copyright_file, license_dir / (abi + '-copyright'))
    licenses.append({'abi': abi, 'package': base_name, 'version': base['Version'],
                     'filename': base['Filename'], 'sha256': base['SHA256'],
                     'copyright_sha256': sha(copyright_file)})
    records.append({'abi': abi, 'package': name, 'version': row['Version'],
                    'source': row['Source'], 'architecture': row['Architecture'],
                    'filename': row['Filename'], 'bytes': int(row['Size']),
                    'sha256': row['SHA256'], 'depends': row['Depends'],
                    'url': config['base'] + row['Filename']})
(root / 'evidence').mkdir(exist_ok=True)
(root / 'evidence/ubuntu-packages.json').write_text(json.dumps(
    {'signature_verified': True, 'signing_fingerprint': config['signing_fingerprint'],
     'release_sha256': config['release_sha256'], 'indices': indices,
     'packages': records, 'licenses': licenses, 'host_packages_installed': False}, indent=2) + '\n')
print(json.dumps(records, indent=2))
