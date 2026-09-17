#!/usr/bin/env python3
"""Publish to our branch using a private index, without touching the build worktree."""
import datetime, hashlib, json, os, subprocess, tarfile
from pathlib import Path
r=Path(__file__).resolve().parents[1]
repo=r.parent/'rmerlin-integration-20260916/integration.git'
base='e4323d78fb137f626de246ac9c663e0662cc375b'
branch='refs/heads/gt-be98-systemd257-services'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
manifest=json.loads((r/'physical-publication-manifest.json').read_text())
assert sha(r/'physical-publication.tar')==manifest['tar_sha256']
backup=json.loads((r/'physical-backup-manifest.json').read_text())
assert sha(r/backup['archive'])==backup['sha256']
stage=r/'reviewed-physical-publication';stage.mkdir(exist_ok=False)
with tarfile.open(r/'physical-publication.tar') as tar:tar.extractall(stage,filter='data')
for name,digest in manifest['files'].items():assert sha(stage/name)==digest,name
assert len(manifest['files'])==sum(p.is_file() for p in stage.rglob('*'))
prefix=stage/'gt-be98/userspace/rc-ssh'
result=json.loads((prefix/'result.json').read_text())
assert result['firmware_flashed'] and not result['firmware_committed']
assert result['physical']['ram_trial_accepted'] and result['physical']['committed_partition']==2
assert result['rootfs_headroom_bytes']>=0 and all(s['passed'] for s in result['suites'].values())
physical=json.loads((prefix/'flash/evidence/physical-receipt.json').read_text())
assert physical['fallback_and_bootloader_unchanged'] and physical['failed_systemd_units']==0
assert physical['hardware_acceleration']['advancing_flows']>0
env=dict(os.environ,GIT_INDEX_FILE=str(r/'physical-publication.index'),GIT_AUTHOR_NAME='leonpano2006',
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
(r/'physical-publication-diff-stat.txt').write_text(git('diff','--stat',base,tree)+'\n')
message='gt-be98: validate leon8 SSH service on physical hardware\n\nFlash only inactive slot1 and verify readback against the published image.\nPreserve the committed fallback and bootloader; use one-shot trial boot.\nVerify the foreground Dropbear cgroup, repeated start, ASUS restart callback,\nfresh SSH login and unchanged host keys. Retain all existing rc services.\n\nPass radio, hardware flow counter progress, web, OpenVPN, runtime ABI,\nsystemd crypto/compression, and Docker default/custom bridge network checks.\nRecord flash/test scripts and verified receipts with dual-host backups.\n\nAccept only the current RAM trial; slot1 stays uncommitted and normal reboot\nstill selects slot2. No firmware commit or bootloader update is performed.\n\nCo-authored-by: Codex <noreply@openai.com>\n'
commit=git('commit-tree',tree,'-p',base,input=message.encode())
git('update-ref',branch,commit,base)
git('fsck','--connectivity-only','--no-dangling',commit)
with (r/'physical-publication-push.log').open('w') as log:
    subprocess.run(['git','--git-dir='+str(repo),'push','fork',branch+':'+branch],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
assert git('ls-remote','fork',branch).split()[0]==commit
receipt={'commit':commit,'parent':base,'tree':tree,'branch':branch,
    'repository':'https://github.com/leonpano2006/asuswrt-merlin.ng-gt-be98',
    'files':len(manifest['files']),'firmware_flashed':True,'firmware_committed':False,
    'backup_sha256_verified':backup['sha256'],'original_worktree_untouched':True,
    'published_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(r/'physical-publication-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
git('bundle','create',str(r/'rc-ssh-physical-since-e4323d7.bundle'),branch,'^'+base)
git('bundle','verify',str(r/'rc-ssh-physical-since-e4323d7.bundle'))
print(json.dumps(receipt,indent=2))
