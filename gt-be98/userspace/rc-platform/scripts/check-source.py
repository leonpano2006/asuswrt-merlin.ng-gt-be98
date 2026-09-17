from pathlib import Path
import json,subprocess,tempfile,shutil
from common import sha
r=Path(__file__).resolve().parents[1]
names=('services.c','usb.c','rc-services.c','rc-services.h')
with tempfile.TemporaryDirectory(prefix='leon-platform-source-') as tmp:
 base=Path(tmp);dst=base/'release/src/router/rc';dst.mkdir(parents=True)
 for n in names:shutil.copy2(r/'saved-inputs'/n,dst/n)
 p=subprocess.run(['patch','--batch','-p1','--input',str(r/'patches/platform-services.patch')],cwd=base,capture_output=True,text=True)
 assert not p.returncode,p.stdout+p.stderr
 for n in names:assert sha(dst/n)==sha(r/'src'/n),n
for n in names:
 p=subprocess.run(['git','diff','--no-index','--check',str(r/'saved-inputs'/n),str(r/'src'/n)],capture_output=True,text=True)
 assert not p.stdout and not p.stderr,p.stdout+p.stderr
record={'saved_base_patch_applies_exactly':True,'source_whitespace_check':True,'new_units':23,
'files':{p.name:sha(p) for p in (r/'src').iterdir() if p.is_file()},'units':{p.name:sha(p) for p in (r/'units').glob('*.service')}}
(r/'evidence/source-review.json').write_text(json.dumps(record,indent=2)+'\n')
print('SOURCE_AND_PATCH_VERIFIED')
