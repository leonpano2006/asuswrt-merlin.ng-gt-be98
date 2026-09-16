#!/usr/bin/env python3
"""Authenticate GCC 15's source package through Ubuntu's signed archive index."""
import hashlib,json,lzma,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
config=json.loads((root/'configs/sources.json').read_text())
cache=root.parent/'libgcc-runtime-20260916/downloads'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
release=cache/'questing-InRelease'
assert sha(release)==config['ubuntu_release']['release_sha256']
gpg=subprocess.run(['gpgv','--status-fd','1','--keyring','/usr/share/keyrings/ubuntu-archive-keyring.gpg',str(release)],capture_output=True,text=True,check=True)
assert '[GNUPG:] VALIDSIG '+config['ubuntu_release']['signing_fingerprint']+' ' in gpg.stdout
indices={};active=False
for line in release.read_text().splitlines():
 if line=='SHA256:':active=True
 elif active and line.startswith(' '):
  digest,size,name=line.split();indices[name]=(digest,int(size))
 elif active:active=False
index=cache/'questing-universe-arm64-Packages.xz'
digest,size=indices['universe/binary-arm64/Packages.xz']
assert sha(index)==digest and index.stat().st_size==size
found=[]
for block in lzma.decompress(index.read_bytes()).decode().split('\n\n'):
 lines=block.splitlines()
 if 'Package: gcc-15-source' not in lines:continue
 row=dict(line.split(': ',1) for line in lines if ': ' in line and not line.startswith(' '))
 if row['Version']==config['gcc15']['version']:found.append(row)
assert len(found)==1
row=found[0];archive=root/'downloads'/config['gcc15']['filename']
assert row['SHA256']==sha(archive)==config['gcc15']['sha256']
assert int(row['Size'])==archive.stat().st_size==config['gcc15']['bytes']
inner=root/'sources/gcc15-package/usr/src/gcc-15/gcc-15.2.0.tar.xz'
assert inner.is_file()
gcc16=(root/config['gcc16']['archive']).resolve(strict=True)
assert sha(gcc16)==config['gcc16']['sha256']
report=dict(ubuntu_source_authenticated=True,signing_fingerprint=config['ubuntu_release']['signing_fingerprint'],
 release_sha256=sha(release),index_sha256=sha(index),source_package_sha256=sha(archive),
 gcc15_inner_archive_sha256=sha(inner),gcc15_upstream_version='15.2.0',
 gcc16_archive_sha256=sha(gcc16),gcc16_version='16.2.0',gcc16_existing_toolchain_dependency=True)
(root/'evidence/source-authentication.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
