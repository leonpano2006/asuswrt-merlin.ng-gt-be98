#!/usr/bin/env python3
"""Advance the existing candidate branch using a checked private index."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,tarfile
r=Path('/home/leonpano/amng-out/less-full-20260917')
repo=Path('/home/leonpano/amng-out/rmerlin-integration-20260916/integration.git')
base='66b518eb544205d05ed57f99c89ebde07bf1a704'
parent='refs/heads/gt-be98-systemd257-services'
branch='refs/heads/gt-be98-systemd257-services'
manifest=json.loads((r/'publication-manifest.json').read_text())
assert hashlib.sha256((r/'publication.tar').read_bytes()).hexdigest()==manifest['tar_sha256']
stage=r/'reviewed-publication';stage.mkdir(exist_ok=False)
with tarfile.open(r/'publication.tar') as tar:tar.extractall(stage,filter='tar')
for name,digest in manifest['files'].items():
    p=stage/name;assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
assert len(manifest['files'])==sum(p.is_file() for p in stage.rglob('*'))
for label in ('less704-systemd257','less704-services257'):
    result=json.loads((stage/'gt-be98/userspace/less-full/evidence/qemu'/label/'result.json').read_text())
    assert result['tests_complete'] and result['guest_complete'] and not result['panic']
env=dict(os.environ,GIT_INDEX_FILE=str(r/'publication.index'),GIT_AUTHOR_NAME='leonpano2006',
    GIT_AUTHOR_EMAIL='leonpano20060507@gmail.com',GIT_COMMITTER_NAME='leonpano2006',
    GIT_COMMITTER_EMAIL='leonpano20060507@gmail.com',GIT_TERMINAL_PROMPT='0')
def git(*args,input=None):
    return subprocess.check_output(['git','--git-dir='+str(repo),*args],input=input,env=env).decode().strip()
assert git('rev-parse',parent)==base
assert git('ls-remote','fork',parent).split()[0]==base
assert git('ls-remote','fork',branch).split()[0]==base
assert git('for-each-ref','--format=%(objectname)',branch)==base
git('read-tree',base)
for p in sorted(x for x in stage.rglob('*') if x.is_file()):
    name=p.relative_to(stage).as_posix();existing=git('ls-tree',base,'--',name)
    mode=existing.split()[0] if existing else ('100755' if p.stat().st_mode&0o111 else '100644')
    oid=git('hash-object','-w','--stdin',input=p.read_bytes())
    git('update-index','--add','--cacheinfo',mode,oid,name)
tree=git('write-tree')
prefix='gt-be98/userspace/less-full/'
git('diff','--check',base,tree,'--',*(prefix+x for x in ('scripts','configs','live','README.md')))
(r/'publication-diff-stat.txt').write_text(git('diff','--stat',base,tree)+'\n')
message='''gt-be98: install full less 704 for systemd paging

Build upstream less natively for Cortex-A53 with GCC 16.2 and firmware
glibc 2.44/tinfo. Replace the BusyBox applet alias without touching BusyBox.
Include lesskey, lessecho, OSC8 helper and manuals in the candidate rootfs.

For the currently running read-only a3 image, use a checked read-only
OverlayFS and a guarded USB mount hook. Live SSH PTY tests verify systemctl,
journalctl, UTF-8, color and search. Preserve the committed fallback.

Include exact build inputs and replay code. Both systemd 257 QEMU suites
pass again; lossless basename ordering keeps zstd-22 within 734 reserved
UBI blocks. The new complete firmware remains unflashed.

Co-authored-by: Codex <noreply@openai.com>
'''
commit=git('commit-tree',tree,'-p',base,input=message.encode())
git('update-ref',branch,commit,base)
with (r/'publication-fsck.log').open('w') as log:
    subprocess.run(['git','--git-dir='+str(repo),'fsck','--connectivity-only','--no-dangling',commit],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
with (r/'publication-push.log').open('w') as log:
    subprocess.run(['git','--git-dir='+str(repo),'push','fork',branch+':'+branch],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
assert git('ls-remote','fork',branch).split()[0]==commit
record={'commit':commit,'parent':base,'tree':tree,'branch':branch,'files':len(manifest['files']),
    'published_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'repository':'https://github.com/leonpano2006/asuswrt-merlin.ng-gt-be98',
    'less_hardware_tested':True,'whole_firmware_hardware_tested':False,'firmware_commit_performed':False,'original_worktree_untouched':True}
(r/'publication-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
bundle=r/'less704-since-66b518.bundle';git('bundle','create',str(bundle),branch,'^'+base)
git('bundle','verify',str(bundle))
(r/'bundle-receipt.json').write_text(json.dumps({'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),
    'bytes':bundle.stat().st_size,'requires':base,'commit':commit},indent=2)+'\n')
print(json.dumps(record),flush=True)
