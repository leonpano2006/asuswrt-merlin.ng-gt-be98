#!/usr/bin/env python3
from pathlib import Path
import concurrent.futures, json, subprocess
r=Path(__file__).resolve().parents[1];root=r/'build/production-rootfs'
# Ordering changes only SquashFS storage placement. Modes, data and paths stay fixed.
files=[]
for p in root.rglob('*'):
 if p.is_file() and not p.is_symlink():
  with p.open('rb') as f: header=f.read(20)
  group=('elf-'+str(int.from_bytes(header[18:20],'little')) if header[:4]==b'\x7fELF' else p.suffix.lower() or 'text')
  files.append((p.relative_to(root).as_posix(),group,p.stat().st_size))
for label,key in [('type',lambda x:(x[1],x[0])),('type-size',lambda x:(x[1],-x[2],x[0]))]:
 rows=sorted(files,key=key);(r/'build'/('sort-'+label+'.txt')).write_text(''.join(name.replace(' ','\\ ')+' '+str(32000-i)+'\n' for i,(name,_,_) in enumerate(rows)))
def run(label):
 out=r/'build'/('layout-'+label+'.squashfs');assert not out.exists()
 cmd=['mksquashfs',str(root),str(out),'-noappend','-all-root','-comp','zstd','-Xcompression-level','22','-b','1048576','-processors','3','-mem','256M','-no-progress','-exit-on-error','-mkfs-time','1789560000']
 if label=='no-tail':cmd+=['-no-tailends']
 else:cmd+=['-tailends','-sort',str(r/'build'/('sort-'+label+'.txt'))]
 with (r/'build'/('layout-'+label+'.log')).open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
 return {'layout':label,'bytes':out.stat().st_size,'command':cmd}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,['type','type-size','no-tail']))
(r/'evidence/compression-layouts.json').write_text(json.dumps(results,indent=2)+'\n');print([(x['layout'],x['bytes']) for x in results])
