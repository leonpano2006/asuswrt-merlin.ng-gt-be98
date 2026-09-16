#!/usr/bin/env python3
"""Publish reviewed source and public evidence without modifying any worktree."""
from pathlib import Path
import os,subprocess,hashlib,json,tarfile,datetime
r=Path('/home/leonpano/amng-out/rmerlin-httpd-fix-20260917')
repo=Path('/home/leonpano/amng-out/rmerlin-integration-20260916/integration.git')
base='dc72164482512481a62517f0f14e86c2fa3cf776';branch='refs/heads/gt-be98-102.9-integration'
manifest=json.loads((r/'publication-manifest.json').read_text())
assert hashlib.sha256((r/'publication.tar').read_bytes()).hexdigest()==manifest['tar_sha256']
stage=r/'reviewed-publication';stage.mkdir(exist_ok=False)
with tarfile.open(r/'publication.tar') as t:t.extractall(stage,filter='tar')
for name,sha in manifest['files'].items():
 p=stage/name;assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==sha,name
 assert not any(l.startswith((b'<<<<<<< ',b'>>>>>>> ')) for l in p.read_bytes().splitlines()),name
assert len(manifest['files'])==sum(p.is_file() for p in stage.rglob('*'))
trial=json.loads((stage/'gt-be98/userspace/rmerlin-httpd-fix/flash/evidence/trial-result.json').read_text())
assert trial['physical_pass'] and not trial['firmware_commit_performed']
assert trial['fallback_unchanged'] and trial['loader_unchanged']
env=dict(os.environ,GIT_INDEX_FILE=str(r/'publication.index'),GIT_AUTHOR_NAME='leonpano2006',GIT_AUTHOR_EMAIL='leonpano20060507@gmail.com',GIT_COMMITTER_NAME='leonpano2006',GIT_COMMITTER_EMAIL='leonpano20060507@gmail.com',GIT_TERMINAL_PROMPT='0')
def git(*args,input=None):return subprocess.check_output(['git','--git-dir='+str(repo),*args],input=input,env=env).decode().strip()
assert git('rev-parse',branch)==base
assert git('ls-remote','fork',branch).split()[0]==base
git('read-tree',base)
for p in sorted(x for x in stage.rglob('*') if x.is_file()):
 name=p.relative_to(stage).as_posix();existing=git('ls-tree',base,'--',name)
 mode=existing.split()[0] if existing else ('100755' if p.stat().st_mode&0o111 else '100644')
 oid=git('hash-object','-w','--stdin',input=p.read_bytes());git('update-index','--add','--cacheinfo',mode,oid,name)
tree=git('write-tree')
message='''gt-be98: fix fortified IPsec and web translation bounds

GCC 15 FORTIFY_SOURCE=3 exposed two existing bounds errors during the
RMerlin 102.9 physical trial: rc stored eth0 plus NUL in four bytes, and
httpd used a complete buffer size for an interior translation pointer.
Use checked IFNAMSIZ copies and bounded tag substitution while retaining
memory checks, model blobs, the #36 kernel and the real split TLS ABIs.

Include actual release/ source fixes, replay scripts, regression tests,
physical results and failed-trial findings. QEMU passes the old-failure
reproducers, new bounds regressions and systemd shutdown. The final a3
image passes management login/pages, four radios, OpenVPN service,
TLS/DNS and Docker DNS/HTTP/HTTPS/LAN/memcg on hardware. Flow counters
confirm hardware acceleration remains active. This is not a line-rate
benchmark or a test of new hardware AQM.

The 90,840,140-byte zstd-22 image was written/read back on inactive slot 1
and booted once. Slot 2 and bootloader hashes are unchanged. No firmware
commit: normal reboot still selects the committed #35 fallback.

Co-authored-by: Codex <noreply@openai.com>
'''
commit=git('commit-tree',tree,'-p',base,input=message.encode());git('update-ref',branch,commit,base)
subprocess.run(['git','--git-dir='+str(repo),'fsck','--connectivity-only','--no-dangling',commit],env=env,check=True,stdout=(r/'publication-fsck.log').open('w'),stderr=subprocess.STDOUT)
with (r/'publication-push.log').open('w') as log:subprocess.run(['git','--git-dir='+str(repo),'push','fork',branch+':'+branch],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
assert git('ls-remote','fork',branch).split()[0]==commit
record={'commit':commit,'parent':base,'tree':tree,'branch':branch,'published_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':len(manifest['files']),'firmware_commit_performed':False,'original_worktree_untouched':True,'repository':'https://github.com/leonpano2006/asuswrt-merlin.ng-gt-be98'}
(r/'publication-receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
bundle=r/'physical-fixes-since-dc721.bundle';git('bundle','create',str(bundle),branch,'^'+base);git('bundle','verify',str(bundle))
(r/'bundle-receipt.json').write_text(json.dumps({'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),'bytes':bundle.stat().st_size,'requires':base,'commit':commit},indent=2)+'\n')
