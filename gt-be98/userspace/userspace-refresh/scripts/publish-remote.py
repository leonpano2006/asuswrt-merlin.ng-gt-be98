#!/usr/bin/env python3
"""Advance our candidate branch with a private Git index and compare-and-swap."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

r = Path(__file__).resolve().parents[1]
repo = r.parent / 'rmerlin-integration-20260916/integration.git'
base = '4ca2d195ebd74525bc7eef3bbd51778990bb15b7'
branch = 'refs/heads/gt-be98-systemd257-services'
manifest = json.loads((r / 'publication-manifest.json').read_text())
assert hashlib.sha256((r / 'publication.tar').read_bytes()).hexdigest() == manifest['tar_sha256']
stage = r / 'reviewed-publication'
stage.mkdir(exist_ok=False)
with tarfile.open(r / 'publication.tar') as tar: tar.extractall(stage, filter='data')
for name, digest in manifest['files'].items():
    assert hashlib.sha256((stage / name).read_bytes()).hexdigest() == digest, name
assert len(manifest['files']) == sum(p.is_file() for p in stage.rglob('*'))
prefix = 'gt-be98/userspace/userspace-refresh/'
result = json.loads((stage / prefix / 'builds/qemu/crypto-v2/result.json').read_text())
assert result['tests_complete'] and result['guest_complete'] and not result['panic']
assert json.loads((stage / prefix / 'evidence/openssl4-upstream-tests.json').read_text())['exit_code'] == 0
assert json.loads((stage / prefix / 'evidence/systemd-openssl4-native-test.json').read_text())['exit_code'] == 0
env = dict(os.environ, GIT_INDEX_FILE=str(r / 'publication.index'), GIT_AUTHOR_NAME='leonpano2006',
           GIT_AUTHOR_EMAIL='leonpano20060507@gmail.com', GIT_COMMITTER_NAME='leonpano2006',
           GIT_COMMITTER_EMAIL='leonpano20060507@gmail.com', GIT_TERMINAL_PROMPT='0')
def git(*args, input=None):
    return subprocess.check_output(['git', '--git-dir=' + str(repo), *args], input=input, env=env).decode().strip()
assert git('rev-parse', branch) == base
assert git('ls-remote', 'fork', branch).split()[0] == base
git('read-tree', base)
for path in sorted(p for p in stage.rglob('*') if p.is_file()):
    name = path.relative_to(stage).as_posix()
    oid = git('hash-object', '-w', '--stdin', input=path.read_bytes())
    git('update-index', '--add', '--cacheinfo', '100644', oid, name)
tree = git('write-tree')
git('diff', '--check', base, tree)
(r / 'publication-diff-stat.txt').write_text(git('diff', '--stat', base, tree) + '\n')
message = '''gt-be98: stage isolated ARM64 OpenSSL 4 and audit userspace updates

Build unmodified OpenSSL 4.0.2 with GCC 16.2/glibc 2.44 for Cortex-A53.
Keep all existing ARM32 libraries, the openssl CLI, and ASUS config intact.
Include replay code, ABI inventory, official version evidence and dependency
records. zstd 1.5.7 is already the latest stable release.

Validate 334 selected upstream tests, systemd 257 OpenSSL API tests, and an
offline #36/Cortex-A53 VM covering cross-ABI TLS 1.3 and encrypted credentials.
Retain systemd 257: 261's kernel baseline and cgroup layout are incompatible.

This is an uninstalled component, not a flashable firmware: adding the full
overlay exceeds the current slot1 rootfs allowance by 3067904 bytes at zstd 22.
Other version updates remain an audited queue; no router state was changed.

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
           'files': len(manifest['files']), 'published_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'router_modified': False, 'firmware_commit_performed': False,
           'original_worktree_untouched': True}
(r / 'publication-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
git('bundle', 'create', str(r / 'userspace-refresh-since-4ca2d19.bundle'), branch, '^' + base)
git('bundle', 'verify', str(r / 'userspace-refresh-since-4ca2d19.bundle'))
print(json.dumps(receipt, indent=2))
