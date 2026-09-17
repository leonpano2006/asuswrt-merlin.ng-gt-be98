#!/usr/bin/env python3
"""Save and verify the actual sources, SDK, tested binaries and replay evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

r = Path(__file__).resolve().parents[1]
saved = r / 'saved-inputs'
saved.mkdir(exist_ok=True)
shutil.copy2(r.parent / 'multiarch-loader-20260916/saved-inputs/Image36', saved / 'Image36')
old = r.parent / 'systemd-upgrade-20260917'
shutil.copy2(next((old / 'sources').glob('systemd-*.tar.gz')), saved)
shutil.copy2(old / 'configs/sources.json', saved / 'systemd-source.json')
names = ['README.md', 'UPDATES.md', 'result.json', 'scripts', 'configs', 'tests', 'evidence', 'overlay',
         'sdk', 'saved-inputs', 'sources/openssl-4.0.2.tar.gz', 'sources/openssl-4.0.2.tar.gz.sha256',
         'sources/source-records.json', 'builds/qemu', 'build/crypto-qemu-v2/guest.cpio.gz',
         'build/crypto-qemu-v2/manifest.json', 'build/size-probe.squashfs', 'build/cc', 'build/run-target']
names += ['build/openssl4/' + x for x in ['libcrypto.so.4', 'libssl.so.4', 'providers/legacy.so', 'apps/openssl']]
names += ['build/systemd-openssl4/' + x for x in ['systemd', 'systemd-executor', 'systemd-journald',
          'systemctl', 'journalctl', 'systemd-creds', 'test-openssl',
          'src/shared/libsystemd-shared-257.so', 'src/core/libsystemd-core-257.so', 'config.h']]
archive = r / 'openssl4-userspace-checkpoint.tar.zst'
assert not archive.exists()
tar = subprocess.Popen(['tar', '-C', str(r), '--exclude=__pycache__', '--sort=name', '-cf', '-', *names], stdout=subprocess.PIPE)
with archive.open('wb') as output:
    compress = subprocess.run(['zstd', '-T4', '-19', '--no-progress', '-c'], stdin=tar.stdout, stdout=output, check=True)
tar.stdout.close()
assert tar.wait() == 0
process = subprocess.Popen(['zstd', '-dc', str(archive)], stdout=subprocess.PIPE)
count = 0
with tarfile.open(fileobj=process.stdout, mode='r|') as stream:
    for member in stream:
        path = r / member.name
        if member.isfile():
            with path.open('rb') as local:
                assert hashlib.file_digest(stream.extractfile(member), 'sha256').digest() == hashlib.file_digest(local, 'sha256').digest(), member.name
            assert member.mode == (path.stat().st_mode & 0o7777), member.name
        elif member.issym():
            assert member.linkname == str(path.readlink()), member.name
        count += 1
process.stdout.close()
assert process.wait() == 0
with archive.open('rb') as f: digest = hashlib.file_digest(f, 'sha256').hexdigest()
record = {'archive': archive.name, 'sha256': digest, 'bytes': archive.stat().st_size,
          'verified_members': count, 'individual_file_contents_modes_and_links_verified': True,
          'parent_checkpoints_and_external_GCC_toolchains_still_required': True}
(r / 'backup-receipt.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
