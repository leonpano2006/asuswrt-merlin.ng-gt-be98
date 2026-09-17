"""Archive exact sources, retained dependencies, firmware and raw test evidence."""
import datetime,json,subprocess
from pathlib import Path
from common import sha
r=Path(__file__).resolve().parents[1]
assert json.loads((r/'result.json').read_text())['status']=='offline-validated candidate; not flashed'
paths=['README.md','result.json','scripts','configs','tests','src','units','patches','evidence','builds/qemu','saved-inputs','candidate','build/rc','build/probes','build/platform-release.squashfs','build/platform-v7/guest.cpio.gz','build/platform-v7/production-preservation.json','build/closure-guest.cpio.gz']
archive=r/'rc-platform-complete-v2.tar.zst';assert not archive.exists()
subprocess.run(['tar','--zstd','-cf',str(archive),'-C',str(r),'--exclude=__pycache__',*paths],check=True)
d={'archive':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive),'contents':paths,'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(r/'backup-manifest.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
