#!/usr/bin/env python3
"""Advance the existing candidate branch using a checked private index."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,tarfile
r=Path('/home/leonpano/amng-out/less-full-20260917/postflash')
repo=Path('/home/leonpano/amng-out/rmerlin-integration-20260916/integration.git')
base='ee4c093fcb9293fad386a5e30f16f98d14b1080a'
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
git('diff','--check',base,tree,'--',*(prefix+x for x in ('scripts','configs','live','flash/scripts','README.md')))
(r/'publication-diff-stat.txt').write_text(git('diff','--stat',base,tree)+'\n')
physical=json.loads((stage/'gt-be98/userspace/less-full/flash/evidence/trial-result.json').read_text())
assert physical['physical_pass'] and physical['ram_acceptance_only']
assert not physical['firmware_commit_performed']
message='''gt-be98: record passing systemd 257 and less 704 hardware trial

Flash inactive slot 1 from the committed #35 fallback, validate payload
readback, and boot once. Record actual cron scheduling and rc restart, LAN
GETINFO, default/login pager behavior, web/TLS management, userspace and
Docker network/memcg checks. Hardware acceleration counters advance.

Keep slot 2 committed with flags 0/1. Only accept this session in RAM; no
firmware commit is performed. Include guarded flash/validation code and
public results; exclude raw journals, private settings and credentials.

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
    'less_hardware_tested':True,'whole_firmware_hardware_tested':True,'firmware_commit_performed':False,'original_worktree_untouched':True}
(r/'publication-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
bundle=r/'physical-trial-since-ee4c093.bundle';git('bundle','create',str(bundle),branch,'^'+base)
git('bundle','verify',str(bundle))
(r/'bundle-receipt.json').write_text(json.dumps({'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),
    'bytes':bundle.stat().st_size,'requires':base,'commit':commit},indent=2)+'\n')
print(json.dumps(record),flush=True)
