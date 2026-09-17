#!/usr/bin/env python3
"""Apply SSH supervision to the physically tested leon7 image, preserving all else."""
from pathlib import Path
import json
import shutil
import subprocess
from common import sha, inventory
r=Path(__file__).resolve().parents[1];w=r.parent
base=w/'systemd-features-20260917/build/production-rootfs';root=r/'build/production-rootfs'
assert sha(base/'usr/sbin/rc')=='ca786145c19101bbfd4bb540aff3fbd3895d7dc47a2a7d476319d0a4009226a8'
assert not root.exists()
subprocess.run(['cp','-a','--reflink=auto',str(base),str(root)],check=True)
files={'usr/sbin/rc':r/'build/rc/rc.stripped',
       'usr/libexec/leon-service-exec':r/'build/rc/leon-service-exec',
       'usr/libexec/leon-service-owner-check':r/'src/leon-service-owner-check',
       'usr/lib/systemd/system/asus-sshd.service':r/'units/asus-sshd.service'}
for name,source in files.items():
    dest=root/name
    if dest.exists():dest.chmod(0o644)
    shutil.copy2(source,dest)
    dest.chmod(0o644 if name.endswith('.service') else 0o755)
meta=root/'usr/share/leon-upstream.json';meta.chmod(0o644)
data=json.loads(meta.read_text());data.update(version='3006.102.9-beta1-leon8',
    service_split=['haveged','crond','infosvr','mdns','ntpd','sshd'],
    base_checkpoint='systemd-features-20260917',
    ssh_supervision='rc configures host/auth keys and policy; systemd owns foreground Dropbear and its sessions')
meta.write_text(json.dumps(data,indent=2)+'\n')
before=inventory(base);after=inventory(root)
delta={n:after.get(n) for n in before.keys()|after.keys() if before.get(n)!=after.get(n)}
assert delta.keys()==files.keys()|{'usr/share/leon-upstream.json'},delta.keys()
(r/'evidence/production-delta.json').write_text(json.dumps({'parent':'systemd-features-20260917',
    'changed':delta,'all_other_paths_identical':True,
    'unchanged_kernel_modules':sum(n.endswith('.ko') for n in before)},indent=2)+'\n')
print('PRODUCTION_ROOT_PREPARED',len(delta),'changed or added paths')
