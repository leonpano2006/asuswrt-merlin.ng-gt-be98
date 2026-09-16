#!/usr/bin/env python3
"""Create an explicit candidate branch in the user's fork using a private index."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,tarfile
r=Path('/home/leonpano/amng-out/systemd-upgrade-20260917')
repo=Path('/home/leonpano/amng-out/rmerlin-integration-20260916/integration.git')
base='0f9e311424bcaacc118f581d3602ba15ec2675dc'
parent='refs/heads/gt-be98-102.9-integration'
branch='refs/heads/gt-be98-systemd257-services'
manifest=json.loads((r/'publication-manifest.json').read_text())
assert hashlib.sha256((r/'publication.tar').read_bytes()).hexdigest()==manifest['tar_sha256']
stage=r/'reviewed-publication';stage.mkdir(exist_ok=False)
with tarfile.open(r/'publication.tar') as tar:tar.extractall(stage,filter='tar')
for name,digest in manifest['files'].items():
    p=stage/name;assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
assert len(manifest['files'])==sum(p.is_file() for p in stage.rglob('*'))
for label in ('systemd257-v5','services257-v5'):
    result=json.loads((stage/'gt-be98/userspace/systemd257-services/evidence/qemu'/label/'result.json').read_text())
    assert result['tests_complete'] and result['guest_complete'] and not result['panic']
env=dict(os.environ,GIT_INDEX_FILE=str(r/'publication.index'),GIT_AUTHOR_NAME='leonpano2006',
    GIT_AUTHOR_EMAIL='leonpano20060507@gmail.com',GIT_COMMITTER_NAME='leonpano2006',
    GIT_COMMITTER_EMAIL='leonpano20060507@gmail.com',GIT_TERMINAL_PROMPT='0')
def git(*args,input=None):
    return subprocess.check_output(['git','--git-dir='+str(repo),*args],input=input,env=env).decode().strip()
assert git('rev-parse',parent)==base
assert git('ls-remote','fork',parent).split()[0]==base
assert not git('ls-remote','fork',branch)
assert not git('for-each-ref','--format=%(objectname)',branch)
git('read-tree',base)
for p in sorted(x for x in stage.rglob('*') if x.is_file()):
    name=p.relative_to(stage).as_posix();existing=git('ls-tree',base,'--',name)
    mode=existing.split()[0] if existing else ('100755' if p.stat().st_mode&0o111 else '100644')
    oid=git('hash-object','-w','--stdin',input=p.read_bytes())
    git('update-index','--add','--cacheinfo',mode,oid,name)
tree=git('write-tree')
# Raw serial logs retain CR bytes and original source snapshots retain their
# upstream whitespace. Check edited program paths and authored tooling only.
prefix='gt-be98/userspace/systemd257-services/'
git('diff','--check',base,tree,'--','release/src/router/rc',
    *(prefix+x for x in ('scripts','tests','units','configs','src/leon-cgroup-prepare',
      'src/leon-service-owner-check','src/leon-cron-drain','src/leon-systemd-prepare',
      'README.md','OWNERSHIP.md','PODMAN.md')))
(r/'publication-diff-stat.txt').write_text(git('diff','--stat',base,tree)+'\n')
message='''gt-be98: stage systemd 257.13 and split cron and discovery services

Upgrade the manager, tools and private libraries together using the A53
GCC 16.2/glibc 2.44 sysroot. Premount the existing v1 resource controllers
and use upstream hybrid hierarchy handling on the retained 4.19 kernel.

Route actual rc cron/infosvr entry points to systemd with no duplicate
supervision or error fallback. Preserve running cron jobs on ordinary
restarts, and drain the owned job cgroup before storage shutdown.
Retain the published IPsec and HTTPD bounds fixes, all 182 kernel modules,
the signed bootfs and early-init rollback monitor.

Include replay code, exact dependency hashes and both passing Cortex-A53
QEMU suites. The zstd-22 candidate fits 734 reserved UBI blocks without
removing features or reducing per-volume reserve. This candidate has not
yet been flashed or accepted on hardware. Podman remains a documented
follow-up; rootless, unified-v2 device filtering and nftables need work.

Co-authored-by: Codex <noreply@openai.com>
'''
commit=git('commit-tree',tree,'-p',base,input=message.encode())
git('update-ref',branch,commit,'0'*40)
with (r/'publication-fsck.log').open('w') as log:
    subprocess.run(['git','--git-dir='+str(repo),'fsck','--connectivity-only','--no-dangling',commit],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
with (r/'publication-push.log').open('w') as log:
    subprocess.run(['git','--git-dir='+str(repo),'push','fork',branch+':'+branch],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
assert git('ls-remote','fork',branch).split()[0]==commit
record={'commit':commit,'parent':base,'tree':tree,'branch':branch,'files':len(manifest['files']),
    'published_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'repository':'https://github.com/leonpano2006/asuswrt-merlin.ng-gt-be98',
    'hardware_tested':False,'firmware_commit_performed':False,'original_worktree_untouched':True}
(r/'publication-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
bundle=r/'systemd257-since-0f9e311.bundle';git('bundle','create',str(bundle),branch,'^'+base)
git('bundle','verify',str(bundle))
(r/'bundle-receipt.json').write_text(json.dumps({'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),
    'bytes':bundle.stat().st_size,'requires':base,'commit':commit},indent=2)+'\n')
print(json.dumps(record),flush=True)
