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
base = '1cdad62d3ce94f9ce7525822ab05224312bd0c6e'
branch = 'refs/heads/gt-be98-systemd257-services'
manifest = json.loads((r / 'publication-manifest.json').read_text())
assert hashlib.sha256((r / 'publication.tar').read_bytes()).hexdigest() == manifest['tar_sha256']
stage = r / 'reviewed-publication-physical-v2'
stage.mkdir(exist_ok=False)
with tarfile.open(r / 'publication.tar') as tar: tar.extractall(stage, filter='data')
for name, digest in manifest['files'].items():
    assert hashlib.sha256((stage / name).read_bytes()).hexdigest() == digest, name
assert len(manifest['files']) == sum(p.is_file() for p in stage.rglob('*'))
prefix = 'gt-be98/userspace/armhf-release/'
result = json.loads((stage / prefix / 'builds/qemu/armhf-usb-v2/result.json').read_text())
assert result['guest_complete'] and not result['panic'] and 'LAB_ARMHF_ALL_PASS' in result['lab_lines']
assert json.loads((stage / prefix / 'evidence/qemu-verification.json').read_text())['all_five_runtime_probe_sets_passed_before_and_after_cache']
assert json.loads((stage / prefix / 'evidence/final-leon6-v2.json').read_text())['headroom_bytes'] >= 0

physical = json.loads((stage / prefix / 'flash/evidence/physical-receipt.json').read_text())
assert physical['ram_trial_accepted'] and not physical['firmware_committed'] and physical['committed_partition'] == 2

env = dict(os.environ, GIT_INDEX_FILE=str(r / 'publication-physical-v2.index'), GIT_AUTHOR_NAME='leonpano2006',
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
message = """gt-be98: record successful uncommitted leon6 hardware trial

Verify inactive-slot flash readback and unchanged rollback/bootloader.
Boot leon6 #36 once with systemd and external USB ARMHF runtimes. Pass
five modern/legacy runtime probes, authenticated web/rc restart, radios,
OpenVPN, mDNS/NTP service ownership and exact changed-file hashes.

Observe advancing hardware L2 flow counters with L2/L3 acceleration
still enabled. Verify Docker default/custom bridge DNS, HTTP, HTTPS and
LAN published port, then remove temporary test containers/networks.

Accept only the RAM trial marker. Slot1 remains uncommitted; committed
slot2 is still the next normal boot target. Save actual probe scripts,
checksums and receipts; this is bounded testing, not a permanent commit.

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
           'router_modified': True, 'router_change': 'authorized inactive-slot flash and RAM-accepted physical trial; firmware remains uncommitted', 'firmware_commit_performed': False,
           'original_worktree_untouched': True}
(r / 'publication-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
git('bundle', 'create', str(r / 'armhf-release-since-1cdad62.bundle'), branch, '^' + base)
git('bundle', 'verify', str(r / 'armhf-release-since-1cdad62.bundle'))
print(json.dumps(receipt, indent=2))
