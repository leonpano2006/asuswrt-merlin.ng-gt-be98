#!/usr/bin/env python3
"""Allow-list source/replay/public evidence; exclude binaries and private state."""
from pathlib import Path
import shutil,json,tarfile,hashlib
r=Path(__file__).resolve().parents[1];w=r.parent;out=r/'publish';out.mkdir(exist_ok=False)
for name in ['rc/rc_ipsec.c','httpd/ej.c']:
 rel=Path('release/src/router')/name;dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(w/'rmerlin-integration-20260916/source-tree'/rel,dst)
for dirname,public in [('rmerlin-ipsec-fix-20260916','rmerlin-ipsec-fix'),('rmerlin-httpd-fix-20260917','rmerlin-httpd-fix')]:
 src=w/dirname;dest=out/'gt-be98/userspace'/public;dest.mkdir(parents=True)
 for sub in ['scripts','tests','patches','configs','src','saved-inputs']:
  if not (src/sub).exists():continue
  for p in (src/sub).rglob('*'):
   if not p.is_file() or '__pycache__' in p.parts:continue
   if p.suffix not in ['.py','.sh','.bash','.c','.h','.patch','.json','.pem']:continue
   target=dest/p.relative_to(src);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 shutil.copy2(src/'README.md',dest/'README.md')
 for p in (src/'evidence').glob('*.json'):
  target=dest/'evidence'/p.name;target.parent.mkdir(exist_ok=True);shutil.copy2(p,target)
 for p in (src/'builds/qemu').rglob('*'):
  if p.name not in ['result.json','serial.log']:continue
  target=dest/'evidence/qemu'/p.relative_to(src/'builds/qemu');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 for p in (src/'candidate').glob('*.manifest.json'):
  target=dest/'evidence'/p.name;target.parent.mkdir(exist_ok=True);shutil.copy2(p,target)
 for p in (src/'flash/scripts').glob('*'):
  if not p.is_file():continue
  target=dest/'flash/scripts'/p.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 for name in ['final-health.txt','trial-result.json','web-check.json','https-management.json','network-config-comparison.json','boot-health.json','live-systemd.txt','live-haveged.txt','live-upstream.txt','live-upstream-corrected-fixture.txt','runtime-hashes.txt','docker-network.txt','docker-lan-memcg.txt','acceleration-stable-flows.txt','httpd-notification.txt','verify-written.txt','ram-acceptance.txt']:
  p=src/'flash/evidence'/name
  if not p.exists():continue
  target=dest/'flash/evidence'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 p=src/'flash/expected-runtime.sha256';target=dest/'flash/expected-runtime.sha256';shutil.copy2(p,target)
p=out/'gt-be98/userspace/rmerlin-upstream/README.md';p.parent.mkdir(parents=True);shutil.copy2(w/'rmerlin-integration-20260916/README.md',p)
files={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
assert 'release/src/router/httpd/ej.c' in files and 'release/src/router/rc/rc_ipsec.c' in files
for p in out.rglob('*'):
 if p.is_file():
  assert '/private/' not in p.as_posix() and p.stat().st_size<2_000_000,p
  assert not p.read_bytes().startswith(b'\x7fELF'),p
archive=r/'publication.tar'
with tarfile.open(archive,'w') as t:
 for name in sorted(files):t.add(out/name,arcname=name)
(r/'publication-manifest.json').write_text(json.dumps({'files':files,'tar_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},indent=2)+'\n');print(len(files),'reviewed files',archive.stat().st_size,'tar bytes')
