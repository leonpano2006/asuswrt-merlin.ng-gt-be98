from pathlib import Path
import json,shutil,subprocess
from common import sha,inventory
r=Path(__file__).resolve().parents[1];w=r.parent
base=w/'systemd-rc-ssh-20260917/build/production-rootfs';root=r/'build/production-rootfs'
assert sha(base/'usr/sbin/rc')=='0e09d9bcbc4ebd312ac8bc759f2b5ea845d74967222b7c21eaaded954df069d6'
assert not root.exists()
subprocess.run(['cp','-a','--reflink=auto',str(base),str(root)],check=True)
files={'usr/sbin/rc':r/'build/rc/rc.stripped','usr/libexec/leon-daemon-supervisor':r/'build/rc/leon-daemon-supervisor'}
for p in (r/'units').iterdir():files['usr/lib/systemd/system/'+p.name]=p
for name,source in files.items():
 dest=root/name
 if dest.exists():dest.chmod(0o644)
 shutil.copy2(source,dest);dest.chmod(0o644 if name.endswith('.service') else 0o755)
meta=root/'usr/share/leon-upstream.json';meta.chmod(0o644)
d=json.loads(meta.read_text());d.update(version='3006.102.9-beta1-leon9',base_checkpoint='systemd-rc-ssh-20260917',platform_service_split=[p.stem.removeprefix('asus-') for p in (r/'units').iterdir()])
meta.write_text(json.dumps(d,indent=2)+'\n')
before=inventory(base);after=inventory(root)
delta={n:after.get(n) for n in before.keys()|after.keys() if before.get(n)!=after.get(n)}
assert delta.keys()==files.keys()|{'usr/share/leon-upstream.json'},delta.keys()
(r/'evidence/production-delta.json').write_text(json.dumps({'parent':'systemd-rc-ssh-20260917','changed':delta,'all_other_paths_identical':True,'unchanged_kernel_modules':sum(n.endswith('.ko') for n in before)},indent=2)+'\n')
print('PRODUCTION_ROOT_PREPARED',len(delta))
