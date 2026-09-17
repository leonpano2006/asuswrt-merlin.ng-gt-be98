#!/usr/bin/env python3
"""Publish to our branch using a private index, without touching the build worktree."""
import datetime, hashlib, json, os, subprocess, tarfile
from pathlib import Path
r=Path(__file__).resolve().parents[1]
repo=r.parent/'rmerlin-integration-20260916/integration.git'
base='61553213b844a0528f0c5436cfe30b4815d5b265'
branch='refs/heads/gt-be98-systemd257-services'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
manifest=json.loads((r/'publication-manifest.json').read_text())
assert sha(r/'publication.tar')==manifest['tar_sha256']
backup=json.loads((r/'backup-manifest.json').read_text())
assert sha(r/backup['archive'])==backup['sha256']
stage=r/('reviewed-publication-'+manifest['tar_sha256'][:12]);stage.mkdir(exist_ok=False)
with tarfile.open(r/'publication.tar') as tar:tar.extractall(stage,filter='data')
for name,digest in manifest['files'].items():assert sha(stage/name)==digest,name
assert len(manifest['files'])==sum(p.is_file() for p in stage.rglob('*'))
prefix=stage/'gt-be98/userspace/httpd-dashboard-fix'
result=json.loads((prefix/'result.json').read_text())
assert result['production_https_traffic_rounds']==30
assert result['old_arm_reproducer_sigabrt'] and result['exported_abi_unchanged']
assert not result['firmware_flashed'] and not result['firmware_committed']
env=dict(os.environ,GIT_INDEX_FILE=str(r/'publication.index'),GIT_AUTHOR_NAME='leonpano2006',
    GIT_AUTHOR_EMAIL='leonpano20060507@gmail.com',GIT_COMMITTER_NAME='leonpano2006',
    GIT_COMMITTER_EMAIL='leonpano20060507@gmail.com',GIT_TERMINAL_PROMPT='0')
def git(*args,input=None):
    return subprocess.check_output(['git','--git-dir='+str(repo),*args],input=input,env=env).decode().strip()
assert git('rev-parse',branch)==base
assert git('ls-remote','fork',branch).split()[0]==base
for name,digest in manifest['base_shared_files'].items():
    content=subprocess.check_output(['git','--git-dir='+str(repo),'show',base+':release/src/router/shared/'+name],env=env)
    assert hashlib.sha256(content).hexdigest()==digest,name
git('read-tree',base)
for path in sorted(p for p in stage.rglob('*') if p.is_file()):
    oid=git('hash-object','-w','--stdin',input=path.read_bytes())
    mode='100755' if path.stat().st_mode&0o111 else '100644'
    git('update-index','--add','--cacheinfo',mode,oid,path.relative_to(stage).as_posix())
tree=git('write-tree')
assert manifest['files']['gt-be98/userspace/httpd-dashboard-fix/src/misc.c'] == manifest['files']['release/src/router/shared/misc.c']
git('diff','--check',base,tree,'--','.',
    ':(exclude)gt-be98/userspace/httpd-dashboard-fix/patches/netdev-wireless-unit.patch',
    ':(exclude)gt-be98/userspace/httpd-dashboard-fix/src/misc.c')
(r/'publication-diff-stat.txt').write_text(git('diff','--stat',base,tree)+'\n')
message='gt-be98: fix Game Dashboard abort for physical wireless names\n\nParse wlN and wlN.M with get_ifname_unit in shared netdev_calc instead\nof subtracting an absent dot pointer and overflowing the snprintf bound.\nValidate radio indices, fall back to list position on invalid input and\nretain FORTIFY, ARMEL GCC 15.2/glibc 2.44 and Cortex-A53 CRC/crypto flags.\n\nReproduce the old SIGABRT under ARM QEMU and pass 16 parser cases.\nVerify the unchanged 1459-symbol ABI, 20 isolated and 30 regular HTTPS\ntraffic rounds, all four radio counters and an actual Chrome dashboard\nlogin. Apply a RAM-only library fix to leon8; no firmware flash, commit\nor network restart. Save exact build dependencies and binaries on DGX\nand ML350; the existing leon9 image still requires rebuilding with this\nlibrary before flashing.\n\nCo-authored-by: Codex <noreply@openai.com>\n'
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
git('bundle','create',str(r/'httpd-fix-since-6155321.bundle'),branch,'^'+base)
git('bundle','verify',str(r/'httpd-fix-since-6155321.bundle'))
print(json.dumps(receipt,indent=2))
