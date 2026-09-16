#!/usr/bin/env python3
"""Private checkpoint of source, sysroot, built objects and exact tested images."""
from pathlib import Path
import argparse,hashlib,json,subprocess,tarfile
from common import sha,inventory
r=Path(__file__).resolve().parents[1];w=r.parent
p=argparse.ArgumentParser();p.add_argument('--output',default='preflash-backup.tar.zst');args=p.parse_args()
assert Path(args.output).name==args.output and args.output.endswith('.tar.zst')
folders=['scripts','configs','src','tests','units','patches','saved-inputs','evidence','candidate',
         'sources','sdk','overlay','build/systemd','build/rc','build/probes',
         'builds/qemu/systemd257-v5','builds/qemu/services257-v5']
paths=[]
for folder in folders:
    base=r/folder
    paths += [p for p in base.rglob('*') if (p.is_file() or p.is_symlink()) and '__pycache__' not in p.parts]
paths += [r/x for x in ('README.md','OWNERSHIP.md','PODMAN.md','build/cc','build/run-target',
    'build/rootfs.squashfs','build/systemd257-v5/guest.cpio.gz','build/systemd257-v5/production-preservation.json')]
paths=sorted(set(paths))
record={str(p.relative_to(w)):({'target':str(p.readlink())} if p.is_symlink() else
    {'sha256':sha(p),'bytes':p.stat().st_size}) for p in paths}
manifest=r/'backup-members.json';manifest.write_text(json.dumps(record,indent=2)+'\n')
archive=r/args.output;assert not archive.exists()
with archive.open('xb') as output:
    proc=subprocess.Popen(['zstd','-T4','-3','-c'],stdin=subprocess.PIPE,stdout=output)
    with tarfile.open(fileobj=proc.stdin,mode='w|') as tar:
        for p in paths+[manifest]:tar.add(p,arcname=str(p.relative_to(w)),recursive=False)
    proc.stdin.close();assert proc.wait()==0
archive.chmod(0o600)
proc=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE)
seen=set()
with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
    for member in tar:
        if member.name not in record:continue
        expected=record[member.name];seen.add(member.name)
        if member.issym():assert member.linkname==expected['target']
        elif member.islnk():
            assert member.linkname in seen
            assert record[member.linkname]['sha256']==expected['sha256']
        else:
            with tar.extractfile(member) as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected['sha256'],member.name
proc.stdout.close();assert proc.wait()==0;assert seen==set(record)
receipt={'file':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive),
    'verified_members':len(seen),'private':True,'contains_source_sdk_objects_candidate_and_qemu':True,
    'external_parent_requirements':'evidence/external-inputs.json'}
(r/'backup-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
