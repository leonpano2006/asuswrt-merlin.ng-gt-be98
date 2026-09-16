#!/usr/bin/env python3
"""Apply the reviewed userspace delta to the physical-tested a3 rootfs."""
from pathlib import Path
import json
import shutil
import subprocess
from common import inventory,sha
r=Path(__file__).resolve().parents[1];w=r.parent
base=w/'rmerlin-httpd-fix-20260917/build/production-rootfs';root=r/'build/production-rootfs'
assert sha(base/'usr/sbin/rc')=='7a8a660ed0dcc2e06fa9ed25518f4271ad42f85b08188bdad2425d34e2cc9f07'
assert sha(base/'usr/sbin/httpd')=='e1c6013f9e535cd76294a4acc814b5b985fb487e79dff60066b18d52cd8bf450'
if not root.exists():subprocess.run(['cp','-a','--reflink=auto',str(base),str(root)],check=True)
def copy(src,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.is_file():dest.chmod(0o755)
    shutil.copy2(src,dest)
    dest.chmod(0o755 if src.suffix not in ('.service','.json') else 0o644)
for file in (r/'overlay').rglob('*'):
    if file.is_file():copy(file,root/file.relative_to(r/'overlay'))
for name in ('core','shared'):
    old=root/f'usr/lib/aarch64-linux-gnu/systemd/libsystemd-{name}-255.so'
    if old.exists():old.unlink()
copy(r/'build/rc/rc.stripped',root/'usr/sbin/rc')
for file in (r/'units').glob('*.service'):copy(file,root/'usr/lib/systemd/system'/file.name)
for name in ('leon-cgroup-prepare','leon-service-owner-check','leon-cron-drain'):copy(r/'src'/name,root/'usr/libexec'/name)
rc_unit=root/'usr/lib/systemd/system/asus-rc.service'
rc_unit.chmod(0o644)
rc_unit.write_text((base/'usr/lib/systemd/system/asus-rc.service').read_text().replace(
    'Requires=systemd-journald.service\n',
    'Requires=systemd-journald.service asus-cron-cleanup.service\nAfter=asus-cron-cleanup.service\n'))
shutil.copy2(rc_unit,r/'units/asus-rc.service')
prepare=(base/'usr/libexec/leon-systemd-prepare').read_text()
prepare=prepare.replace('/usr/sbin/ldconfig\n','/usr/sbin/ldconfig\n/usr/libexec/leon-cgroup-prepare\n')
(r/'src/leon-systemd-prepare').write_text(prepare)
copy(r/'src/leon-systemd-prepare',root/'usr/libexec/leon-systemd-prepare')
meta=root/'usr/share/leon-upstream.json';meta.chmod(0o644)
d=json.loads(meta.read_text());d.update(version='3006.102.9-beta1-leon4',
    systemd='257.13',service_split=['haveged','crond','infosvr'],
    cgroup='hybrid; v1 cpuacct/memory/devices/freezer/pids retained')
meta.write_text(json.dumps(d,indent=2)+'\n')
before=inventory(base);after=inventory(root)
changed={name for name in before if before[name]!=after.get(name)}
added=set(after)-set(before)
allowed={'usr/sbin/rc','usr/libexec/leon-systemd-prepare','usr/share/leon-upstream.json','usr/lib/systemd/system/asus-rc.service',
    'usr/lib/aarch64-linux-gnu/systemd/libsystemd-core-255.so',
    'usr/lib/aarch64-linux-gnu/systemd/libsystemd-shared-255.so'}
allowed|={str(f.relative_to(r/'overlay')) for f in (r/'overlay').rglob('*') if f.is_file()}
assert not changed-allowed,changed-allowed
assert all(before[k]==after[k] for k in before if k.endswith('.ko'))
probes=r/'build/probes';probes.mkdir(exist_ok=True)
for f in (w/'rmerlin-httpd-fix-20260917/build/probes').iterdir():
    dst=probes/f.name
    if dst.exists():dst.unlink()
    shutil.copy2(f,dst)
for name in ('more-services-check.sh','cron-child-test','cgroup-check.sh'):
    copy(r/'tests'/name,probes/name)
(r/'evidence/production-delta.json').write_text(json.dumps({'parent':'rmerlin-httpd-fix-20260917',
    'changed_or_removed_paths':sorted(changed),'added_paths':sorted(added),
    'unchanged_kernel_modules':sum(k.endswith('.ko') for k in before),
    'production_init_sha256':sha(root/'usr/sbin/init'),'rc_sha256':sha(root/'usr/sbin/rc'),
    'httpd_a3_retained':True},indent=2)+'\n')
print('PRODUCTION_ROOT_PREPARED',len(changed),'changed;',len(added),'added')
