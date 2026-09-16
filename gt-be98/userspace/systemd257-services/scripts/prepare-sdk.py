#!/usr/bin/env python3
from pathlib import Path
import subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];old=r.parent/'systemd-lab-20260916'
assert not (r/'sdk').exists()
subprocess.run(['cp','-a','--reflink=auto',str(old/'sdk'),str(r/'sdk')],check=True)
for name in ['cc','run-target']:
 p=r/'build'/name;p.write_text((old/'build'/name).read_text().replace(str(old/'sdk'),str(r/'sdk')));p.chmod(0o755)
record={'source_sdk':old.name,'source_record':json.loads((old/'evidence/sdk.json').read_text()),'compiler_version':subprocess.check_output([str(r/'build/cc'),'-dumpfullversion'],text=True).strip(),'native_aarch64':True,'glibc':'2.44','cpu':'cortex-a53+crc+crypto','libraries':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (r/'sdk/usr/lib/aarch64-linux-gnu').glob('*.so*') if p.is_file() and not p.is_symlink()}}
assert record['compiler_version']=='16.2.0'
(r/'evidence/sdk.json').write_text(json.dumps(record,indent=2)+'\n')
