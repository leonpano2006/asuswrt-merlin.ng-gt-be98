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
base = '8b6fb608c985269b0c59cc71ae4f3436d10c6aa2'
branch = 'refs/heads/gt-be98-systemd257-services'
manifest = json.loads((r / 'publication-manifest.json').read_text())
assert hashlib.sha256((r / 'publication.tar').read_bytes()).hexdigest() == manifest['tar_sha256']
stage = r / 'reviewed-publication'
stage.mkdir(exist_ok=False)
with tarfile.open(r / 'publication.tar') as tar: tar.extractall(stage, filter='data')
for name, digest in manifest['files'].items():
    assert hashlib.sha256((stage / name).read_bytes()).hexdigest() == digest, name
assert len(manifest['files']) == sum(p.is_file() for p in stage.rglob('*'))
prefix = 'gt-be98/userspace/armhf-usb/'
result = json.loads((stage / prefix / 'builds/qemu/armhf-usb/result.json').read_text())
assert result['guest_complete'] and not result['panic'] and 'LAB_ARMHF_ALL_PASS' in result['lab_lines']
assert json.loads((stage / prefix / 'evidence/qemu-verification.json').read_text())['all_armhf_tests_passed']
assert json.loads((stage / prefix / 'result.json').read_text())['usb_payload_installed']

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
message = """gt-be98: externalize ARMHF runtime to an independent USB directory

Replace the candidate arm-linux-gnueabihf directory with a symlink to a
versioned system-libs directory directly on the USB root. Do not use
/usr/local. Keep ARMEL/AArch64 boot runtimes and all other applications.

Save 1695744 compressed bytes on the optimized OpenSSL 4 candidate; it
still exceeds the existing slot1 allowance by 692224 bytes, so no flashable
image is generated. Include the staging, audit, and validation scripts.

Verify 330 native/ARMEL loader closures without USB, ARMHF runtime/C++
probes before and after ldconfig with USB, and missing-USB behavior in
kernel #36 QEMU. Install only the versioned payload on real USB and pass
explicit-path runtime probes. Original live libraries, bootstate and
hardware acceleration remain unchanged; no flash or firmware commit.

Co-authored-by: Codex <noreply@openai.com>
"""

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
           'router_modified': True, 'router_change': 'additive USB payload and temporary probes only', 'firmware_commit_performed': False,
           'original_worktree_untouched': True}
(r / 'publication-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
git('bundle', 'create', str(r / 'armhf-usb-since-8b6fb60.bundle'), branch, '^' + base)
git('bundle', 'verify', str(r / 'armhf-usb-since-8b6fb60.bundle'))
print(json.dumps(receipt, indent=2))
