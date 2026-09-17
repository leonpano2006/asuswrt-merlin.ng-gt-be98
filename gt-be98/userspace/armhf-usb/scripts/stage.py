#!/usr/bin/env python3
"""Move the entire ARM hard-float directory to a versioned external USB payload."""
import hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent
sys.path.insert(0,str(w/'multiarch-loader-20260916/scripts'))
from common import inventory,inventory_sha
source=w/'rootfs-slim-20260917/build/optimized-rootfs'
triplet='arm-linux-gnueabihf';relative='usr/lib/'+triplet
original=inventory(source/relative)
digest=inventory_sha(original)
usb_relative='system-libs/gt-be98/'+digest[:16]+'/'+triplet
target='/tmp/mnt/JFFS/'+usb_relative
root=r/'build/rootfs';assert not root.exists()
subprocess.run(['cp','-a','--reflink=auto',str(source),str(root)],check=True)
payload=r/'usb-payload'/usb_relative
payload.parent.mkdir(parents=True,exist_ok=True)
shutil.move(str(root/relative),str(payload))
(root/relative).symlink_to(target)
assert inventory(payload)==original
old=inventory(source);new=inventory(root)
assert new[relative]['kind']=='link' and new[relative]['target']==target
for name,row in old.items():
 if name!=relative and not name.startswith(relative+'/'):assert new.get(name)==row,name
assert set(old)-set(new)=={relative+'/'+name for name in original}
record={'link_path':'/'+relative,'link_target':target,'usb_relative':usb_relative,
        'tree_sha256':digest,'files':original,'regular_files':sum(x['kind']=='file' for x in original.values()),
        'raw_bytes':sum(x.get('bytes',0) for x in original.values()),
        'other_firmware_paths_identical':True,'local_prefix_used':False,'router_modified':False}
(r/'evidence/payload.json').write_text(json.dumps(record,indent=2)+'\n')
with tarfile.open(r/'armhf-usb-payload.tar','w') as t:
 def root_owned(member):
  member.uid=member.gid=0;member.uname=member.gname='root';return member
 t.add(r/'usb-payload/system-libs',arcname='system-libs',filter=root_owned)
# Use the same reviewed packer with this checkpoint as its output directory.
(r/'scripts/measure.py').write_text((w/'rootfs-slim-20260917/scripts/measure.py').read_text())
subprocess.run(['python3',str(r/'scripts/measure.py'),str(root),'armhf-external-zstd157','--zstd157'],check=True)
print(json.dumps({k:v for k,v in record.items() if k!='files'},indent=2))
