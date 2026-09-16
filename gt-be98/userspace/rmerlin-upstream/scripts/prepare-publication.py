#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,shutil,tarfile
r=Path(__file__).resolve().parents[1];root=r/'publish/gt-be98/userspace/rmerlin-upstream';root.mkdir(parents=True,exist_ok=False)
for name in ['README.md']:
 shutil.copy2(r/name,root/name)
for name in ['scripts','tests','src','configs','patches']:
 shutil.copytree(r/name,root/name,ignore=shutil.ignore_patterns('__pycache__'))
(root/'evidence').mkdir();(root/'evidence/components').mkdir();(root/'evidence/packages').mkdir();(root/'candidate').mkdir()
selected=['merge-resolutions.json','reviewed-source-overlay.json','component-recipe-evaluation.json','rc-source-changes.json','openssl-build.json','openssl-build-commands.json','openssl-shim-symbol-coverage.json','openssl-shim-coverage-summary.txt','parent-openssl-consumers.json','production-staging.json','rebuilt-elfs.json','source-and-header-inputs.json','isa-macros.json','packaging.json','final-summary.json','compression-layouts.json','webui-build.json','webui-syntax.json','router-readonly-capacity.txt','service-probe-build.json']
for name in selected:shutil.copy2(r/'evidence'/name,root/'evidence'/name)
for c in ['shared','libovpn','rc','httpd','infosvr']:
 # make -p dumps the caller's environment. Publish only actual recipe data.
 raw=(r/'evidence'/(c+'-flags.log')).read_text();compact='\n'.join(l for l in raw.splitlines() if l.startswith(('LEON_','vpath %.c ')))+'\n'
 (root/'evidence'/(c+'-flags.log')).write_text(compact)
 dst=root/'evidence/components'/c;dst.mkdir()
 for name in ['compile-commands.json','link-command.json','inputs.json','result.json']:shutil.copy2(r/'build'/('management-'+c)/name,dst/name)
for c in ['openvpn','tor','strongswan','haveged','inadyn','dnsmasq','miniupnpd','miniupnpd-igdv2']:
 dst=root/'evidence/packages'/c;dst.mkdir()
 for name in ['commands.json','result.json','environment.json']:
  p=r/'build'/('package-'+c)/name
  if p.exists():shutil.copy2(p,dst/name)
for p in (r/'candidate').glob('*.json'):shutil.copy2(p,root/'candidate'/p.name)
shutil.copytree(r/'builds/qemu/upstream-v6',root/'evidence/qemu-upstream-v6')
# Recovery snapshots of every consumed C/header/model object, outside Git.
manifest=json.loads((r/'evidence/source-and-header-inputs.json').read_text())
inputs=set(manifest['headers'])|set(manifest['sources'])
snapshot=r/'saved-inputs';snapshot.mkdir(exist_ok=True)
for name in inputs:
 p=r.parent/name;dest=snapshot/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
(root/'.gitignore').write_text('build/\nbuilds/\nsource-tree/\nsources/\nsaved-inputs/\npublish/\n*.tar\n*.tar.zst\n__pycache__/\ncandidate/*.pkgtb\n')
files=[p for p in root.rglob('*') if p.is_file()]
for p in files:
 data=p.read_bytes()
 assert not re.search(rb'(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', data),p
with tarfile.open(r/'build/checkpoint-publication.tar','w') as t:
 for p in files:t.add(p,arcname=str(p.relative_to(r/'publish')))
record={'files':len(files),'bytes':sum(p.stat().st_size for p in files),'tar_sha256':hashlib.sha256((r/'build/checkpoint-publication.tar').read_bytes()).hexdigest(),'saved_input_count':len(inputs),'toolchain_binaries_in_git':False,'firmware_binaries_in_git':False}
(r/'evidence/publication-snapshot.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
