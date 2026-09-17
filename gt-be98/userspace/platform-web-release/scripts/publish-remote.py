#!/usr/bin/env python3
"""Publish reviewed release tooling/evidence without touching the build checkout."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

r = Path(__file__).resolve().parents[1]
repo = r.parent / 'rmerlin-integration-20260916/integration.git'
branch = 'refs/heads/gt-be98-systemd257-services'
base = 'bccac27b3924dc4687def0600e66d67e88d6fd8e'
def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()
manifest = json.loads((r / 'publication-manifest.json').read_text())
assert sha(r / 'publication.tar') == manifest['tar_sha256']
stage = r / ('reviewed-' + manifest['tar_sha256'][:12])
stage.mkdir()
with tarfile.open(r / 'publication.tar') as tar:
    tar.extractall(stage, filter='data')
for name, digest in manifest['files'].items():
    assert sha(stage / name) == digest
assert len(manifest['files']) == sum(p.is_file() for p in stage.rglob('*'))
result = json.loads((stage / 'gt-be98/userspace/platform-web-release/result.json').read_text())
assert result['physical_checks_passed'] and result['firmware_flashed']
assert result['fallback_and_loader_unchanged'] and not result['firmware_committed']
env = dict(os.environ, GIT_INDEX_FILE=str(r / 'publication.index'),
           GIT_AUTHOR_NAME='leonpano2006', GIT_AUTHOR_EMAIL='leonpano20060507@gmail.com',
           GIT_COMMITTER_NAME='leonpano2006', GIT_COMMITTER_EMAIL='leonpano20060507@gmail.com',
           GIT_TERMINAL_PROMPT='0')
def git(*args, input=None):
    return subprocess.check_output(['git', '--git-dir='+str(repo), *args],
                                   input=input, env=env).decode().strip()
assert git('rev-parse', branch) == base
assert git('ls-remote', 'fork', branch).split()[0] == base
git('read-tree', base)
for path in sorted(p for p in stage.rglob('*') if p.is_file()):
    oid = git('hash-object', '-w', '--stdin', input=path.read_bytes())
    mode = '100755' if path.stat().st_mode & 0o111 else '100644'
    git('update-index', '--add', '--cacheinfo', mode, oid, path.relative_to(stage).as_posix())
tree = git('write-tree')
git('diff', '--check', base, tree)
message = ('gt-be98: package and validate leon10 platform and web fixes\n\n'
           'Combine the platform service split with the validated dashboard and\n'
           'AiMesh fixes. Record exact input and output hashes, zstd level 22\n'
           'capacity checks, signed bootfs preservation, exact-image QEMU loader\n'
           'tests, guarded inactive-slot flashing and physical validation.\n\n'
           'Preserve the committed slot2 fallback and keep slot1 uncommitted.\n'
           'Back up artifacts separately on DGX and ML350.\n\n'
           'Co-authored-by: Codex <noreply@openai.com>\n')
commit = git('commit-tree', tree, '-p', base, input=message.encode())
git('update-ref', branch, commit, base)
git('fsck', '--connectivity-only', '--no-dangling', commit)
git('push', 'fork', branch+':'+branch)
assert git('ls-remote', 'fork', branch).split()[0] == commit
receipt = dict(commit=commit, parent=base, tree=tree, branch=branch,
               repository='https://github.com/leonpano2006/asuswrt-merlin.ng-gt-be98',
               files=len(manifest['files']), original_worktree_untouched=True,
               firmware_committed=False,
               published_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(r / 'publication-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
git('bundle', 'create', str(r / 'leon10-since-bccac27.bundle'), branch, '^'+base)
git('bundle', 'verify', str(r / 'leon10-since-bccac27.bundle'))
print(json.dumps(receipt, indent=2))
