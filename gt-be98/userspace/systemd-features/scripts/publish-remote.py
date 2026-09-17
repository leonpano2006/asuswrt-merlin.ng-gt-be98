#!/usr/bin/env python3
"""Publish to our branch using a private index, without touching the build worktree."""
import datetime, hashlib, json, os, subprocess, tarfile
from pathlib import Path
r=Path(__file__).resolve().parents[1]
repo=r.parent/'rmerlin-integration-20260916/integration.git'
base='ea206ced7a48e30c8be38a49217ef7e36b177aeb'
branch='refs/heads/gt-be98-systemd257-services'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
manifest=json.loads((r/'publication-manifest.json').read_text())
assert sha(r/'publication.tar')==manifest['tar_sha256']
backup=json.loads((r/'backup-manifest.json').read_text())
assert sha(r/backup['archive'])==backup['sha256']
stage=r/'reviewed-publication';stage.mkdir(exist_ok=False)
with tarfile.open(r/'publication.tar') as tar:tar.extractall(stage,filter='data')
for name,digest in manifest['files'].items():assert sha(stage/name)==digest,name
assert len(manifest['files'])==sum(p.is_file() for p in stage.rglob('*'))
prefix=stage/'gt-be98/userspace/systemd-features'
result=json.loads((prefix/'result.json').read_text())
assert not result['firmware_flashed'] and not result['firmware_committed']
assert result['rootfs_headroom_bytes']>=0 and all(s['passed'] for s in result['suites'].values())
for label in ('features-v3','services-v3','network-v3'):
    s=json.loads((prefix/'builds/qemu'/label/'result.json').read_text())
    assert s['guest_complete'] and s['tests_complete'] and not s['panic']
env=dict(os.environ,GIT_INDEX_FILE=str(r/'publication.index'),GIT_AUTHOR_NAME='leonpano2006',
    GIT_AUTHOR_EMAIL='leonpano20060507@gmail.com',GIT_COMMITTER_NAME='leonpano2006',
    GIT_COMMITTER_EMAIL='leonpano20060507@gmail.com',GIT_TERMINAL_PROMPT='0')
def git(*args,input=None):
    return subprocess.check_output(['git','--git-dir='+str(repo),*args],input=input,env=env).decode().strip()
assert git('rev-parse',branch)==base
assert git('ls-remote','fork',branch).split()[0]==base
git('read-tree',base)
for path in sorted(p for p in stage.rglob('*') if p.is_file()):
    oid=git('hash-object','-w','--stdin',input=path.read_bytes())
    mode='100755' if path.stat().st_mode&0o111 else '100644'
    git('update-index','--add','--cacheinfo',mode,oid,path.relative_to(stage).as_posix())
tree=git('write-tree');git('diff','--check',base,tree)
(r/'publication-diff-stat.txt').write_text(git('diff','--stat',base,tree)+'\n')
message='''gt-be98: enable systemd crypto and compression, restore full sysctl

Build the leon7 candidate with OpenSSL, curl, zstd, zlib and blkid enabled
in systemd 257.13. Include procps-ng sysctl, systemd-creds and systemd-sysctl.
Retain ASUS rc/init/units, kernel #36 and all 182 modules unchanged.

Keep the full feature sets of Bash/coreutils and use internal shared glibc
for iperf3. Preserve curl public ABI with upstream symbol hiding and -Oz.
Fit zstd-22 rootfs with 276 KiB headroom and both flasher reserves intact.

Pass real-kernel Cortex-A53 QEMU PID1, rc/service ownership and shutdown,
OpenVPN, cgroup, TLS, journal compression, sysctl and network-tool checks.
Verify 334 loader closures without USB and all five runtime ABI probe sets.
Save build/test code, source and dependency hashes, and verified backups.

Only sysctl was installed live, with read-only checks. The candidate has
not been flashed; firmware commit and rollback state remain unchanged.

Co-authored-by: Codex <noreply@openai.com>
'''
commit=git('commit-tree',tree,'-p',base,input=message.encode())
git('update-ref',branch,commit,base)
git('fsck','--connectivity-only','--no-dangling',commit)
with (r/'publication-push.log').open('w') as log:
    subprocess.run(['git','--git-dir='+str(repo),'push','fork',branch+':'+branch],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
assert git('ls-remote','fork',branch).split()[0]==commit
receipt={'commit':commit,'parent':base,'tree':tree,'branch':branch,
    'repository':'https://github.com/leonpano2006/asuswrt-merlin.ng-gt-be98',
    'files':len(manifest['files']),'firmware_flashed':False,'firmware_committed':False,
    'backup_sha256_verified':backup['sha256'],'original_worktree_untouched':True,
    'published_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(r/'publication-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
git('bundle','create',str(r/'systemd-features-since-ea206.bundle'),branch,'^'+base)
git('bundle','verify',str(r/'systemd-features-since-ea206.bundle'))
print(json.dumps(receipt,indent=2))
