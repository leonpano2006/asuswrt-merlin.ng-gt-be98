#!/usr/bin/env python3
"""Save exact tested inputs privately; verify every archived regular file."""
from pathlib import Path
import hashlib,json,os,stat,subprocess,tarfile
from common import sha
r=Path(__file__).resolve().parents[1]
archive=r/'mdns-ntpd-checkpoint.tar.zst';assert not archive.exists()
selected=['README.md','OWNERSHIP.md','src','scripts','configs','units','tests','patches',
          'saved-inputs','evidence','candidate','build/rc','build/probes',
          'build/production-rootfs','builds/qemu',
          'build/network-services-v5/guest.cpio.gz',
          'build/network-services-v5/production-preservation.json',
          'build/network-services-v5/sort.txt','build/network-services-v5/squashfs.log']
members={}
def describe(p):
    s=p.lstat();entry={'mode':stat.S_IMODE(s.st_mode)}
    if p.is_symlink():entry.update(kind='symlink',target=os.readlink(p))
    elif p.is_dir():entry['kind']='directory'
    elif p.is_file():entry.update(kind='file',sha256=sha(p),bytes=s.st_size)
    else:raise RuntimeError(p)
    members[p.relative_to(r).as_posix()]=entry
for name in selected:
    root=r/name;describe(root)
    if root.is_dir():
        for directory,dirs,files in os.walk(root,followlinks=False):
            for name2 in dirs+files:describe(Path(directory)/name2)
manifest=r/'backup-content.json';manifest.write_text(json.dumps(members,indent=2)+'\n')
subprocess.run(['tar','--hard-dereference','-I','zstd -T4 -12','-cf',str(archive),'-C',str(r),
                *selected,'backup-content.json'],check=True)
subprocess.run(['zstd','-t',str(archive)],check=True,stdout=subprocess.DEVNULL)
proc=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
seen=set()
with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
    for member in tar:
        name=member.name.rstrip('/')
        if name=='backup-content.json':continue
        assert name in members and name not in seen,name
        seen.add(name);row=members[name]
        assert stat.S_IMODE(member.mode)==row['mode'],name
        if row['kind']=='file':
            assert member.isfile() and member.size==row['bytes'],name
            assert hashlib.file_digest(tar.extractfile(member),'sha256').hexdigest()==row['sha256'],name
        elif row['kind']=='symlink':assert member.issym() and member.linkname==row['target'],name
        else:assert member.isdir(),name
assert proc.wait()==0 and seen==members.keys()
record={'archive':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive),
        'verified_members':len(seen),'individual_contents_modes_links_verified':True,
        'parent_checkpoints_required':True}
(r/'backup-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
