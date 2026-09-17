#!/usr/bin/env python3
"""Back up the complete validated checkpoint and prepare source publication."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import tarfile

r = Path(__file__).resolve().parents[1]
def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

result = json.loads((r / 'result.json').read_text())
assert result['status'] == 'live RAM fix validated; next firmware must be repacked'
assert result['qemu_final_all_pass'] and result['production_api_rounds'] == 20
assert result['production_browser_topology_verified']
paths = ['README.md', 'result.json', 'scripts', 'tests', 'src', 'saved-inputs',
         'patches', 'evidence', 'builds/qemu', 'build/httpd', 'build/rc',
         'build/guest.cpio.gz', 'build/read-shm', 'build/aimesh_topology.html']
archive = r / 'aimesh-validated-v2.tar.zst'
assert not archive.exists()
subprocess.run(['tar', '--zstd', '-cf', str(archive), '-C', str(r),
                '--exclude=__pycache__', *paths], check=True)
backup = {'archive': archive.name, 'bytes': archive.stat().st_size, 'sha256': sha(archive),
          'contents': paths, 'excluded': ['private API responses', 'credentials', 'tokens', 'NVRAM', 'private keys'],
          'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
(r / 'backup-manifest.json').write_text(json.dumps(backup, indent=2) + '\n')
files = []
for name in ['README.md', 'result.json', 'backup-manifest.json', 'scripts', 'tests', 'src', 'patches']:
    p = r / name
    files += [p] if p.is_file() else [f for f in p.rglob('*') if f.is_file() and '__pycache__' not in str(f)]
files += list((r / 'evidence').glob('*.json'))
files += [r / 'evidence/production-health.txt', r / 'evidence/ram-apply.txt']
files += list((r / 'builds/qemu').glob('*/result.json'))
prefix = 'gt-be98/userspace/aimesh-ui-fix'
canonical = {'web.c': 'httpd/web.c', 'cfg_slavelist.h': 'cfg_mnt/cfg_slavelist.h',
             'networkmap.h': 'networkmap/networkmap.h', 'aimesh_topology.html': 'www/aimesh/aimesh_topology.html'}
manifest = {}
with tarfile.open(r / 'publication.tar', 'w') as tar:
    for p in sorted(set(files)):
        name = prefix + '/' + p.relative_to(r).as_posix()
        tar.add(p, arcname=name, recursive=False)
        manifest[name] = sha(p)
    for name, relative in canonical.items():
        target = 'release/src/router/' + relative
        tar.add(r / 'src' / name, arcname=target, recursive=False)
        manifest[target] = sha(r / 'src' / name)
    target = 'gt-be98/userspace/rc-platform/candidate/KNOWN-ISSUE-aimesh.json'
    tar.add(r / 'evidence/superseded-candidate.json', arcname=target, recursive=False)
    manifest[target] = sha(r / 'evidence/superseded-candidate.json')
data = {'files': manifest, 'tar_sha256': sha(r / 'publication.tar'),
        'base_files': {'release/src/router/' + relative: sha(r / 'saved-inputs' / name)
                       for name, relative in canonical.items()}}
(r / 'publication-manifest.json').write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'backup': backup, 'publication_files': len(manifest)}, indent=2))
