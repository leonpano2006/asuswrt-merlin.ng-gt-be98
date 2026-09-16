#!/usr/bin/env python3
"""Run the original ASUS dictionary pipeline on the x86 ML350, in isolation."""
from pathlib import Path
import hashlib,json,subprocess,tarfile
r=Path('/home/leonpano/amng-out/rmerlin-integration-20260916'); b=r/'webui-build'; b.mkdir(exist_ok=False)
with tarfile.open(r/'webui-inputs.tar') as t: t.extractall(b,filter='tar')
router=b/'router'; (b/'image').mkdir()
make=(router/'www/Makefile').read_text().replace('include ../common.mak','include ../.config',1)
(router/'www/Makefile.build').write_text(make)
cmd=['make','-f','Makefile.build','install','BUILD_NAME=GT-BE98','HND_ROUTER=y','TOP='+str(router),'SRCBASE='+str(b),'INSTALLDIR='+str(b/'stage')]
with (b/'build.log').open('w') as log: status=subprocess.run(cmd,cwd=router/'www',stdout=log,stderr=subprocess.STDOUT)
if status.returncode: print((b/'build.log').read_text()[-6000:]); raise SystemExit(status.returncode)
# The helper name is an isolated build input, not a router asset.
(b/'stage/www/Makefile.build').unlink(missing_ok=True)
with tarfile.open(r/'webui-output.tar','w') as t:
 for p in (b/'stage').iterdir(): t.add(p,arcname=p.name)
record={'command':cmd,'host':subprocess.check_output(['hostname'],text=True).strip(),'artifact_sha256':hashlib.sha256((r/'webui-output.tar').read_bytes()).hexdigest(),'bytes':(r/'webui-output.tar').stat().st_size}
(b/'result.json').write_text(json.dumps(record,indent=2)+'\n'); print(json.dumps(record,indent=2))
