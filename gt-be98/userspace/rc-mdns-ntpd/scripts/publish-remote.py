#!/usr/bin/env python3
"""Advance only our candidate branch; use a private index and compare-and-swap."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,tarfile
r=Path('/home/leonpano/amng-out/systemd-rc-next-20260917')
repo=Path('/home/leonpano/amng-out/rmerlin-integration-20260916/integration.git')
base='849ef74df2e6f365234bb3c8f1c62ab2a8f9f526'
branch='refs/heads/gt-be98-systemd257-services'
manifest=json.loads((r/'publication-manifest.json').read_text())
assert hashlib.sha256((r/'publication.tar').read_bytes()).hexdigest()==manifest['tar_sha256']
stage=r/'reviewed-publication';stage.mkdir(exist_ok=False)
with tarfile.open(r/'publication.tar') as tar:tar.extractall(stage,filter='tar')
for name,digest in manifest['files'].items():
    p=stage/name;assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
assert len(manifest['files'])==sum(p.is_file() for p in stage.rglob('*'))
prefix='gt-be98/userspace/rc-mdns-ntpd/'
initrd=None
for label in ('network-services-v5','network-services-v5-services','network-services-v5-new'):
    result=json.loads((stage/prefix/'evidence/qemu'/label/'result.json').read_text())
    assert result['tests_complete'] and result['guest_complete'] and not result['panic']
    if initrd:assert result['initramfs_sha256']==initrd
    initrd=result['initramfs_sha256']
env=dict(os.environ,GIT_INDEX_FILE=str(r/'publication.index'),GIT_AUTHOR_NAME='leonpano2006',
    GIT_AUTHOR_EMAIL='leonpano20060507@gmail.com',GIT_COMMITTER_NAME='leonpano2006',
    GIT_COMMITTER_EMAIL='leonpano20060507@gmail.com',GIT_TERMINAL_PROMPT='0')
def git(*args,input=None):
    return subprocess.check_output(['git','--git-dir='+str(repo),*args],input=input,env=env).decode().strip()
assert git('rev-parse',branch)==base
assert git('ls-remote','fork',branch).split()[0]==base
git('read-tree',base)
for p in sorted(x for x in stage.rglob('*') if x.is_file()):
    name=p.relative_to(stage).as_posix();existing=git('ls-tree',base,'--',name)
    mode=existing.split()[0] if existing else ('100755' if p.stat().st_mode&0o111 else '100644')
    oid=git('hash-object','-w','--stdin',input=p.read_bytes())
    git('update-index','--add','--cacheinfo',mode,oid,name)
tree=git('write-tree')
# Check the actual source diff and authored code. Verbatim baseline/snapshot
# copies retain ASUS's unrelated pre-existing whitespace for exact replay.
git('diff','--check',base,tree,'--','release/src/router/rc',
    *(prefix+x for x in ('scripts','units','tests','README.md','OWNERSHIP.md',
                         'src/leon-service-exec.c','src/leon-service-owner-check')))
(r/'publication-diff-stat.txt').write_text(git('diff','--stat',base,tree)+'\n')
message='''gt-be98: move mDNS and NTP lifecycle into systemd services

Keep ASUS configuration and WAN policy in rc while supervising the existing
foreground Avahi and BusyBox NTP daemons. Route USB mDNS refreshes and NTP
synchronization side effects back through the manager, preserving legacy-init
launchers and preventing NTP stop from draining DDNS/VPN descendants.

Include literal argv handoff, ownership guards, the actual four rc source
files, native executor, units, replay scripts, dependency hashes and three
passing offline QEMU suites. Retain the kernel, blobs, full less and all other
production paths. Package with zstd 22 within the existing 734-LEB allowance.

This is an unflashed candidate, not a firmware commit or a hardware result.

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
    'whole_firmware_hardware_tested':False,'flashed':False,
    'firmware_commit_performed':False,'original_worktree_untouched':True}
(r/'publication-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
bundle=r/'mdns-ntpd-since-849ef74.bundle';git('bundle','create',str(bundle),branch,'^'+base)
git('bundle','verify',str(bundle))
(r/'bundle-receipt.json').write_text(json.dumps({'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),
    'bytes':bundle.stat().st_size,'requires':base,'commit':commit},indent=2)+'\n')
print(json.dumps(record),flush=True)
