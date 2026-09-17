#!/usr/bin/env python3
"""Archive the exact candidate, staged runtimes, sources, SDK and raw evidence."""
import datetime, json, subprocess, tarfile
from pathlib import Path
from common import sha
r=Path(__file__).resolve().parents[1]
assert json.loads((r/'result.json').read_text())['status']=='offline-validated candidate; not flashed'
paths=['README.md','result.json','scripts','configs','tests','live','evidence','builds/qemu',
    'overlay','size-overlay','saved-inputs','candidate','sources/curl-8.22.0.tar.xz',
    'sources/procps-ng-4.0.7.tar.xz','build/cc','build/run-target',
    'build/features-final-v2.squashfs','build/features-v3/guest.cpio.gz',
    'build/features-v3/production-preservation.json','build/closure-guest.cpio.gz']
archive=r/'systemd-features-complete.tar.zst';assert not archive.exists()
subprocess.run(['tar','--zstd','-cf',str(archive),'-C',str(r),'--exclude=__pycache__',*paths],check=True)
record={'archive':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive),
    'contents':paths,'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(r/'backup-manifest.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
