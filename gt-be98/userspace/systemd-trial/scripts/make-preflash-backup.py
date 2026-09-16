from pathlib import Path
import hashlib,json,os,stat,tarfile
from common import sha
r=Path(__file__).resolve().parents[1];w=r.parent;files=set()
for folder in ('scripts','src','tests','units','patches','configs','evidence','overlay','sources','saved-inputs','build/ovpn','build/rc','build/probes','builds/qemu','flash'):
 root=r/folder;files.add(root)
 for directory,dirs,names in os.walk(root,followlinks=False):
  dirs[:]=[x for x in dirs if x!='__pycache__']
  files.update(Path(directory)/x for x in dirs+names if x!='__pycache__')
files.update(r/x for x in ('README.md','candidate/GT-BE98_leon36-systemd-trial3_zstd22.pkgtb','candidate/GT-BE98_leon36-systemd-trial3_zstd22.manifest.json','build/rootfs.squashfs','build/boot-final/guest.cpio.gz','build/boot-final/production-preservation.json','build/early-init'))
files.update(w/x for x in ('systemd-rc-compat-20260916/ml350-backup-receipt.json','systemd-lab-20260916/ml350-backup-receipt.json','multiarch-loader-20260916/saved-inputs/Image36'))
rows={}
for p in sorted(files):
 st=p.lstat();row={'mode':stat.S_IMODE(st.st_mode)}
 if p.is_symlink():row.update(kind='link',target=os.readlink(p))
 elif p.is_dir():row['kind']='directory'
 else:row.update(kind='file',bytes=st.st_size,sha256=sha(p))
 rows[str(p.relative_to(w))]=row
manifest=r/'preflash-manifest.json';manifest.write_text(json.dumps(rows,indent=2)+'\n')
archive=r/'systemd-trial3-preflash.tar'
with tarfile.open(archive,'x',dereference=False) as t:
 for p in sorted(files|{manifest}):t.add(p,arcname=p.relative_to(w),recursive=False)
with tarfile.open(archive) as t:
 for name,row in rows.items():
  member=t.getmember(name);assert member.mode==row['mode']
  if row['kind']=='file':
   with t.extractfile(member) as f:assert hashlib.file_digest(f,'sha256').hexdigest()==row['sha256'],name
  elif row['kind']=='link':assert member.issym() and member.linkname==row['target']
  else:assert member.isdir()
receipt={'archive':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive),'verified_members':len(rows)}
(r/'preflash-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
