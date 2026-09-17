#!/usr/bin/env python3
"""Select verified size rebuilds; preserve all other files in the prior candidate."""
import json,shutil,hashlib,sys,subprocess
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent;root=r/'build/rootfs'
for src,rel in [('build/zstd-dynamic-full/zstd','usr/bin/zstd'),('build/sqlite/sqlite3','usr/gnu/bin/sqlite3')]:
 p=root/rel;shutil.copy2(r/src,p);p.chmod(0o755)
 out=r/'overlay'/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
meta=root/'usr/share/leon-upstream.json';data=json.loads(meta.read_text());data.update(version='3006.102.9-beta1-leon6',base_checkpoint='armhf-usb-20260917',openssl_policy='ARM32 3.5.8 and 1.1 BSP closure retained; additive AArch64 OpenSSL 4.0.2',armhf_external='/tmp/mnt/JFFS/system-libs/gt-be98/8da410f090d92cff/arm-linux-gnueabihf',size_rebuilds={'aarch64_libstdc++':'16.2.0 -Oz','armel_libstdc++':'15.2.0 -Oz ARM mode softfp','zstd':'1.5.7 full CLI dynamically linked to existing libzstd','sqlite3':'3.42.0 same engine options -Oz LTO'},trial='uncommitted slot1; slot2 retained')
meta.write_text(json.dumps(data,indent=2)+'\n');out=r/'overlay/usr/share/leon-upstream.json';out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(meta,out)
sys.path.insert(0,str(w/'multiarch-loader-20260916/scripts'));from common import inventory,elf_info
parent=w/'armhf-usb-20260917/build/rootfs';a,b=inventory(parent),inventory(root)
changed={k:{'before':a.get(k),'after':b.get(k)} for k in sorted(set(a)|set(b)) if a.get(k)!=b.get(k)}
expected={'usr/bin/zstd','usr/gnu/bin/sqlite3','usr/lib/aarch64-linux-gnu/libstdc++.so.6.0.36','usr/lib/arm-linux-gnueabi/libstdc++.so.6.0.34','usr/share/leon-upstream.json'}
assert set(changed)==expected,set(changed)
api={}
for rel in expected:
 if 'libstdc++' not in rel:continue
 old,new=elf_info(parent/rel),elf_info(root/rel)
 assert all(k in new['exports'] and new['exports'][k]==v for k,v in old['exports'].items())
 api[rel]={'old_exports':len(old['exports']),'new_exports':len(new['exports']),'all_original_exports_identical':True}
(r/'evidence/final-root-changes.json').write_text(json.dumps({'changes':changed,'cxx_api':api},indent=2)+'\n')
subprocess.run(['python3',str(r/'scripts/measure.py'),str(root),'final-leon6-v2','--zstd157'],check=True)
