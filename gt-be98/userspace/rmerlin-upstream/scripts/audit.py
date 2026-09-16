#!/usr/bin/env python3
from pathlib import Path
import json, os, shlex, sys
from elftools.elf.elffile import ELFFile
r=Path(__file__).resolve().parents[1]; w=r.parent
sys.path.insert(0,str(r/'scripts')); from common import sha,inventory
root=r/'build/production-rootfs';parent=w/'systemd-service-split-20260916/build/production-rootfs'
staging=json.loads((r/'evidence/production-staging.json').read_text()); report=[]
for x in staging['installed']:
 x['sha256']=sha(root/x['path'])
 if not x['elf']:continue
 with (root/x['path']).open('rb') as f:
  e=ELFFile(f);d=e.get_section_by_name('.dynamic');note=e.get_section_by_name('.note.gnu.build-id');flags=e.get_section_by_name('.GCC.command.line')
  row={'path':x['path'],'sha256':x['sha256'],'needed':[z.needed for z in d.iter_tags() if z.entry.d_tag=='DT_NEEDED'] if d else [],'rpath':[str(getattr(z,'rpath',getattr(z,'runpath',''))) for z in d.iter_tags() if z.entry.d_tag in ('DT_RPATH','DT_RUNPATH')] if d else [],'class':e.elfclass,'machine':e.header.e_machine,'build_id':next(note.iter_notes())['n_desc'] if note else None,'flags':flags.data().decode().strip('\0').split('\0') if flags else []}
  assert row['class']==32 and row['machine']=='EM_ARM', row
  assert row['build_id'] and any('cortex-a53' in f for f in row['flags']),row
  assert not any('/' in s for s in row['needed']),row
  assert not any('/home/' in s or '/opt/' in s for s in row['rpath']),row
  report.append(row)
(r/'evidence/rebuilt-elfs.json').write_text(json.dumps(report,indent=2)+'\n')
before=inventory(parent); after=inventory(root)
for name in before:
 if name.endswith('.ko') or name in ('usr/sbin/init','usr/lib/systemd/systemd','usr/lib/arm-linux-gnueabi/libnvram.so'):
  assert before[name]==after[name],name
staging.update(changed=[n for n in before if n in after and before[n]!=after[n]],added=sorted(after.keys()-before.keys()),removed=sorted(before.keys()-after.keys()))
(r/'evidence/production-staging.json').write_text(json.dumps(staging,indent=2)+'\n')
headers={}; sources={}
for component in ('shared','libovpn','rc','httpd','infosvr'):
 b=r/'build'/('management-'+component); cwd=r/'source-tree/release/src/router'/component
 for row in json.loads((b/'inputs.json').read_text()):
  p=Path(row['source']);assert sha(p)==row['sha256'],p;sources[str(p.relative_to(w))]=row
 for dep in b.glob('*.d'):
  names=shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1])
  for name in names:
   p=Path(os.path.abspath(cwd/name));headers[str(p.relative_to(w))]=sha(p)
(r/'evidence/source-and-header-inputs.json').write_text(json.dumps({'sources':sources,'headers':headers},indent=2)+'\n')
print('AUDIT_PASS',len(report),'A53 ELF files with Build ID;',len(sources),'source/object inputs;',len(headers),'headers/source dependencies; no build-host loader paths')
