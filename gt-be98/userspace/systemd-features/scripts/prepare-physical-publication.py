#!/usr/bin/env python3
"""Save raw physical evidence; publish code and whitespace-normalized text logs."""
import io, json, subprocess, tarfile
from pathlib import Path
from common import sha
r=Path(__file__).resolve().parents[1]
receipt=json.loads((r/'flash/evidence/physical-receipt.json').read_text())
assert receipt['ram_trial_accepted'] and not receipt['firmware_committed']
archive=r/'leon7-physical-trial.tar.zst';assert not archive.exists()
paths=['README.md','result.json','scripts','flash/scripts','flash/evidence',
       'flash/expected-files.json','flash/leon7-probes.tar','candidate/'+next((r/'candidate').glob('*.manifest.json')).name]
subprocess.run(['tar','--zstd','-cf',str(archive),'-C',str(r),'--exclude=__pycache__',*paths],check=True)
(r/'physical-backup-manifest.json').write_text(json.dumps({'archive':archive.name,'bytes':archive.stat().st_size,
    'sha256':sha(archive),'base_binary_backup_sha256':receipt['base_binary_backup_sha256'],'contents':paths},indent=2)+'\n')
files=[]
for name in ['README.md','result.json','physical-backup-manifest.json','flash/scripts','flash/evidence','flash/expected-files.json',
             'scripts/record-physical.py','scripts/publish-physical.py','scripts/prepare-physical-publication.py']:
    p=r/name
    files += [p] if p.is_file() else [f for f in p.rglob('*') if f.is_file() and '__pycache__' not in str(f)]
manifest={};import hashlib
with tarfile.open(r/'physical-publication.tar','w') as tar:
    for p in sorted(set(files)):
        raw=p.read_bytes();data=raw
        if p.suffix=='.txt':data=('\n'.join(line.rstrip() for line in raw.decode().splitlines())+'\n').encode()
        name='gt-be98/userspace/systemd-features/'+p.relative_to(r).as_posix()
        info=tarfile.TarInfo(name);info.size=len(data);info.mode=p.stat().st_mode&0o777
        tar.addfile(info,io.BytesIO(data));manifest[name]=hashlib.sha256(data).hexdigest()
(r/'physical-publication-manifest.json').write_text(json.dumps({'files':manifest,'tar_sha256':sha(r/'physical-publication.tar')},indent=2)+'\n')
print('PHYSICAL_PUBLICATION_FILES',len(files),'BACKUP_BYTES',archive.stat().st_size)
