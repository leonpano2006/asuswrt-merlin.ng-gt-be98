#!/usr/bin/env python3
"""Apply only the NTP/mDNS ownership delta to the hardware-tested less704 root."""
from pathlib import Path
import json, shutil, subprocess
from common import sha, inventory
r=Path(__file__).resolve().parents[1];w=r.parent
base=w/'less-full-20260917/build/production-rootfs';root=r/'build/production-rootfs'
assert sha(base/'usr/sbin/rc')=='5191c8a0bc759add07c915682375b986d89d81574535ab910beddbec24e7b87d'
assert not root.exists()
subprocess.run(['cp','-a','--reflink=auto',str(base),str(root)],check=True)
files={'usr/sbin/rc':r/'build/rc/rc.stripped',
       'usr/libexec/leon-service-exec':r/'build/rc/leon-service-exec',
       'usr/libexec/leon-service-owner-check':r/'src/leon-service-owner-check'}
files.update({'usr/lib/systemd/system/'+p.name:p for p in (r/'units').glob('*.service')})
for name,source in files.items():
    dest=root/name
    if dest.exists():dest.chmod(0o644)
    shutil.copy2(source,dest)
    dest.chmod(0o644 if name.endswith('.service') else 0o755)
meta=root/'usr/share/leon-upstream.json';meta.chmod(0o644)
data=json.loads(meta.read_text());data.update(version='3006.102.9-beta1-leon5',
    service_split=['haveged','crond','infosvr','mdns','ntpd'],
    base_checkpoint='less-full-20260917',
    ntp_callback='rc manager owns synchronization side effects')
meta.write_text(json.dumps(data,indent=2)+'\n')
before=inventory(base);after=inventory(root)
delta={n:after.get(n) for n in before.keys()|after.keys() if before.get(n)!=after.get(n)}
assert delta.keys()==files.keys()|{'usr/share/leon-upstream.json'},delta.keys()
(r/'evidence/production-delta.json').write_text(json.dumps({'parent':'less-full-20260917',
    'changed':delta,'all_other_paths_identical':True,
    'unchanged_kernel_modules':sum(n.endswith('.ko') for n in before)},indent=2)+'\n')
print('PRODUCTION_ROOT_PREPARED',len(delta),'changed or added paths')
probes=r/'build/probes';probes.mkdir(parents=True,exist_ok=True)
for source in (w/'systemd-upgrade-20260917/build/probes').iterdir():
    if source.name not in ('services-probe','infosvr-mock','network-services-probe'):
        shutil.copy2(source,probes/source.name)
for name in ('network-services-check.sh','check-network-daemons'):
    shutil.copy2(r/'tests'/name,probes/name)
