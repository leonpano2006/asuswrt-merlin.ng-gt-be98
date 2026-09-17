#!/usr/bin/env python3
"""Publish actual fixes through a private index without touching the build tree."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import tarfile

r = Path(__file__).resolve().parents[1]
repo = r.parent / 'rmerlin-integration-20260916/integration.git'
base = '24de71557a7f6ff4e97d77ceddc96bf4b2dbf17a'
branch = 'refs/heads/gt-be98-systemd257-services'
def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
manifest = json.loads((r / 'publication-manifest.json').read_text())
backup = json.loads((r / 'backup-manifest.json').read_text())
assert sha(r / 'publication.tar') == manifest['tar_sha256']
assert sha(r / backup['archive']) == backup['sha256']
stage = r / ('reviewed-publication-' + manifest['tar_sha256'][:12])
stage.mkdir(exist_ok=False)
with tarfile.open(r / 'publication.tar') as tar:
    tar.extractall(stage, filter='data')
for name, digest in manifest['files'].items():
    assert sha(stage / name) == digest, name
assert len(manifest['files']) == sum(p.is_file() for p in stage.rglob('*'))
prefix = stage / 'gt-be98/userspace/aimesh-ui-fix'
result = json.loads((prefix / 'result.json').read_text())
assert result['production_api_rounds'] == 20 and result['production_browser_topology_verified']
assert result['qemu_final_all_pass'] and not result['firmware_flashed'] and not result['firmware_committed']
env = dict(os.environ, GIT_INDEX_FILE=str(r / 'publication.index'),
           GIT_AUTHOR_NAME='leonpano2006', GIT_AUTHOR_EMAIL='leonpano20060507@gmail.com',
           GIT_COMMITTER_NAME='leonpano2006', GIT_COMMITTER_EMAIL='leonpano20060507@gmail.com',
           GIT_TERMINAL_PROMPT='0')
def git(*args, input=None):
    return subprocess.check_output(['git', '--git-dir=' + str(repo), *args], input=input, env=env).decode().strip()
assert git('rev-parse', branch) == base
assert git('ls-remote', 'fork', branch).split()[0] == base
for name, digest in manifest['base_files'].items():
    content = subprocess.check_output(['git', '--git-dir=' + str(repo), 'show', base + ':' + name], env=env)
    assert hashlib.sha256(content).hexdigest() == digest, name
git('read-tree', base)
for path in sorted(p for p in stage.rglob('*') if p.is_file()):
    oid = git('hash-object', '-w', '--stdin', input=path.read_bytes())
    mode = '100755' if path.stat().st_mode & 0o111 else '100644'
    git('update-index', '--add', '--cacheinfo', mode, oid, path.relative_to(stage).as_posix())
tree = git('write-tree')
git('diff', '--check', base, tree, '--', '.',
    ':(exclude)gt-be98/userspace/aimesh-ui-fix/patches/*',
    ':(exclude)gt-be98/userspace/aimesh-ui-fix/src/*')
(r / 'publication-diff-stat.txt').write_text(git('diff', '--stat', base, tree) + '\n')
message = '''gt-be98: restore AiMesh and client-list shared-memory compatibility

Preserve the ARM32 cfg_server time32 wire layout while retaining application
time64. Match the retained GT-BE98 networkmap producer rather than consuming
new upstream fields absent from its shared segment. Bound both wired-MAC
JSON formatters by remaining capacity and initialize topology as an array.

Compare all cfg/networkmap fields and padding against vendor fixtures under
ARM QEMU. Reproduce two old FORTIFY aborts and pass 18 formatter cases.
Pass the final offline boot regression, 20 production HTTPS API rounds and
actual browser topology/client details with Traditional Chinese labels.
Apply HTTPD and the processed template in RAM; leave the RC broker, mesh
backend, radios, hardware acceleration and firmware rollback unchanged.
The next leon9 image must be repacked with this fix and the dashboard fix.

Co-authored-by: Codex <noreply@openai.com>
'''
commit = git('commit-tree', tree, '-p', base, input=message.encode())
git('update-ref', branch, commit, base)
git('fsck', '--connectivity-only', '--no-dangling', commit)
with (r / 'publication-push.log').open('w') as log:
    subprocess.run(['git', '--git-dir=' + str(repo), 'push', 'fork', branch + ':' + branch],
                   env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
assert git('ls-remote', 'fork', branch).split()[0] == commit
receipt = {'commit': commit, 'parent': base, 'tree': tree, 'branch': branch,
           'repository': 'https://github.com/leonpano2006/asuswrt-merlin.ng-gt-be98',
           'files': len(manifest['files']), 'backup_sha256_verified': backup['sha256'],
           'original_worktree_untouched': True, 'firmware_flashed': False, 'firmware_committed': False,
           'published_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
(r / 'publication-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
git('bundle', 'create', str(r / 'aimesh-fix-since-24de715.bundle'), branch, '^' + base)
git('bundle', 'verify', str(r / 'aimesh-fix-since-24de715.bundle'))
print(json.dumps(receipt, indent=2))
