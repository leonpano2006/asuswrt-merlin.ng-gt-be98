#!/usr/bin/env python3
"""Capacity-only USB split: not a deployable package or a service migration."""
import hashlib, json, shutil, subprocess
from pathlib import Path
r = Path(__file__).resolve().parents[1]
root = r/'build/usb-split-rootfs'
assert not root.exists()
subprocess.run(['cp','-a','--reflink=auto',str(r.parent/'userspace-refresh-20260917/build/size-probe-rootfs'),str(root)],check=True)
# Keep every shared library and boot/service component. These four large
# applications are only a capacity example; startup/config references must
# be audited before a real USB migration is implemented.
names = ['usr/sbin/Tor','usr/sbin/ookla','usr/bin/iperf3','usr/gnu/bin/sqlite3']
manifest = []
for name in names:
    src = root/name
    assert src.is_file() and not src.is_symlink()
    dst = r/'build/usb-payload/libexec/firmware-optional'/src.name
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)
    link = '/usr/local/libexec/firmware-optional/'+src.name
    manifest.append({'original_path':'/'+name,'usb_path':link,
                     'bytes':src.stat().st_size,'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
    src.unlink();src.symlink_to(link)
(r/'evidence/usb-split-files.json').write_text(json.dumps({
    'status':'capacity_simulation_only','files':manifest,
    'functional_dependency_audit_complete':False,'router_modified':False,
    'warning':'USB-unavailable behavior and service ordering not implemented'},indent=2)+'\n')
subprocess.run(['python3',str(r/'scripts/measure.py'),str(root),'usb-split-o2-zstd157','--zstd157'],check=True)
