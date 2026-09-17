#!/usr/bin/env python3
"""Publish to our branch using a private index, without touching the build worktree."""
import datetime, hashlib, json, os, subprocess, tarfile
from pathlib import Path
r=Path(__file__).resolve().parents[1]
repo=r.parent/'rmerlin-integration-20260916/integration.git'
base='e4108078d915e8eb493973d82d41e468bf0c9cf7'
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
prefix=stage/'gt-be98/userspace/rc-platform'
result=json.loads((prefix/'result.json').read_text())
assert not result['firmware_flashed'] and not result['firmware_committed']
assert result['rootfs_headroom_bytes']>=0 and all(s['passed'] for s in result['suites'].values())
for label in ('release-default','release-services','release-network','release-ssh','release-platform','release-real'):
    s=json.loads((prefix/'builds/qemu'/label/'result.json').read_text())
    assert s['guest_complete'] and s['tests_complete'] and not s['panic']
env=dict(os.environ,GIT_INDEX_FILE=str(r/'publication.index'),GIT_AUTHOR_NAME='leonpano2006',
    GIT_AUTHOR_EMAIL='leonpano20060507@gmail.com',GIT_COMMITTER_NAME='leonpano2006',
    GIT_COMMITTER_EMAIL='leonpano20060507@gmail.com',GIT_TERMINAL_PROMPT='0')
def git(*args,input=None):
    return subprocess.check_output(['git','--git-dir='+str(repo),*args],input=input,env=env).decode().strip()
assert git('rev-parse',branch)==base
assert git('ls-remote','fork',branch).split()[0]==base
for name,digest in manifest['base_rc_files'].items():
    content=subprocess.check_output(['git','--git-dir='+str(repo),'show',base+':release/src/router/rc/'+name],env=env)
    assert hashlib.sha256(content).hexdigest()==digest,name
git('read-tree',base)
for path in sorted(p for p in stage.rglob('*') if p.is_file()):
    oid=git('hash-object','-w','--stdin',input=path.read_bytes())
    mode='100755' if path.stat().st_mode&0o111 else '100644'
    git('update-index','--add','--cacheinfo',mode,oid,path.relative_to(stage).as_posix())
tree=git('write-tree')
# Unified diff context has required leading spaces before blank lines/tabs.
# Its application is checked against the saved base; check all actual source here.
# Check actual repository deltas. The checkpoint copies must be byte-identical
# to those checked files; their unchanged legacy whitespace is not a new edit.
for name in ('services.c','usb.c'):
    assert manifest['files']['gt-be98/userspace/rc-platform/src/'+name] == manifest['files']['release/src/router/rc/'+name]
git('diff','--check',base,tree,'--','.',
    ':(exclude)gt-be98/userspace/rc-platform/patches/platform-services.patch',
    ':(exclude)gt-be98/userspace/rc-platform/src/services.c',
    ':(exclude)gt-be98/userspace/rc-platform/src/usb.c')
(r/'publication-diff-stat.txt').write_text(git('diff','--stat',base,tree)+'\n')
message='gt-be98: split platform daemons into systemd units\n\nMove 23 conditional Wi-Fi, logging, USB/share, HTTP and ASUS daemon\nlifecycles to isolated systemd services while rc keeps NVRAM policy,\nconfiguration generation and hardware startup order. Track foreground\nand double-forking programs with a native subreaper using existing\n4.19 PPid interfaces, fixed executable identities and private argv.\nPreserve working directory, timezone, PATH, session/signal setup,\nASUS file-creation mask and Samba CPU affinity. Reject duplicate owners\nand never fall back to untracked launches on managed failures.\n\nPreserve all signed bootfs, kernel #36, 182 modules, acceleration setup,\ntrial bootguard, prior HTTPD/IPsec fixes and six earlier service splits.\nThe hostapd configuration blob and remaining hardware policies stay\nunchanged; hardware validation is pending a physical trial.\n\nPass actual-kernel offline lifecycle/failure/isolation tests, source\ncallpath tests, real logger and SMB negotiation, previous rc/service\nregressions, 335 loader closures and five runtime ABI sets. Fix the\ncron test fixture shutdown race without changing production cron.\nPackage zstd level 22 with 268 KiB rootfs headroom and both flasher\nreserves, and save complete source/artifact backups on DGX and ML350.\n\nCandidate only: no router changes, flashing or firmware commit.\n\nCo-authored-by: Codex <noreply@openai.com>\n'
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
git('bundle','create',str(r/'rc-platform-since-e410807.bundle'),branch,'^'+base)
git('bundle','verify',str(r/'rc-platform-since-e410807.bundle'))
print(json.dumps(receipt,indent=2))
