#!/usr/bin/env python3
"""Stage verified overlays and audit the complete production change set."""
import json, shutil, stat, subprocess
from pathlib import Path
from common import inventory, sha
r=Path(__file__).resolve().parents[1]
base=r.parent/'armhf-release-20260917/build/rootfs'
root=r/'build/production-rootfs'
if not root.exists():
    subprocess.run(['cp','-a','--reflink=auto',str(base),str(root)],check=True)
allowed={'usr/share/leon-upstream.json'}
for name in ('overlay','size-overlay'):
    overlay=r/name
    subprocess.run(['cp','-a',str(overlay)+'/.',str(root)],check=True)
    for p in overlay.rglob('*'):
        rel=p.relative_to(overlay); out=root/rel; old=base/rel
        allowed.add(str(rel))
        if p.is_symlink(): continue
        if p.is_dir(): out.chmod(stat.S_IMODE(old.stat().st_mode) if old.is_dir() else 0o755)
        elif p.is_file(): out.chmod(0o755 if p.stat().st_mode & 0o111 else 0o644)
m=json.loads((base/'usr/share/leon-upstream.json').read_text())
m.update(version='3006.102.9-beta1-leon7',base_checkpoint='armhf-release-20260917',
         systemd='257.13 with OpenSSL, curl, zstd, zlib and blkid',
         sysctl='procps-ng 4.0.7; /usr/sbin/sysctl',libcurl='8.22.0; native AArch64; OpenSSL 4.0.2')
m['size_rebuilds'].update(bash='5.3.15 -Oz LTO; same features',
    coreutils='9.11 -Oz LTO; same applets',libcurl='8.22.0 -Oz LTO; upstream symbol hiding; all configured protocols retained',
    iperf3='3.21 -Oz LTO; dynamic internal glibc; same optional features')
(root/'usr/share/leon-upstream.json').write_text(json.dumps(m,indent=2)+'\n')
a,b=inventory(base),inventory(root)
changed={k for k in a if a[k]!=b.get(k)};added=set(b)-set(a)
assert not changed-allowed,changed-allowed
assert not set(a)-set(b)
modules=[k for k in a if k.endswith('.ko')]
assert all(a[k]==b[k] for k in modules)
units=[k for k in a if k.startswith('usr/lib/systemd/system/')]
assert all(a[k]==b[k] for k in units)
assert a['usr/sbin/rc']==b['usr/sbin/rc']
assert a['usr/sbin/init']==b['usr/sbin/init']
record={'parent':'armhf-release-20260917','changed':sorted(changed),'added':sorted(added),
    'unchanged_modules':len(modules),'unchanged_rc_sha256':sha(root/'usr/sbin/rc'),
    'all_init_units_unchanged':True,'init_unchanged':True,
    'changed_file_records':{k:b[k] for k in sorted(changed|added)}}
(r/'evidence/production-delta.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='changed_file_records'},indent=2))
