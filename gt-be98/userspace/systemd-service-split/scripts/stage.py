#!/usr/bin/env python3
"""Stage the minimal production delta and reuse the complete trial3 regression."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

r = Path(__file__).resolve().parents[1]; w = r.parent
parent = w / 'systemd-trial3-20260916'
sys.path.insert(0, str(parent / 'scripts'))
from common import inventory, sha
base = parent / 'build/production-rootfs'
root = r / 'build/production-rootfs'
assert not root.exists()
subprocess.run(['cp', '-a', '--reflink=auto', str(base), str(root)], check=True)
t = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
subprocess.run([t['tools'] + 'strip', '--strip-unneeded', '-o', str(root / 'usr/sbin/rc'),
                str(r / 'build/rc/rc')], env=dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir']), check=True)
shutil.copy2(r / 'units/asus-haveged.service', root / 'usr/lib/systemd/system/asus-haveged.service')
p = root / 'usr/libexec/leon-haveged-check'
shutil.copy2(r / 'scripts/haveged-check.sh', p); p.chmod(0o755)
before = inventory(base); after = inventory(root)
changed = sorted(n for n in before if before[n] != after[n])
added = sorted(after.keys() - before.keys())
assert changed == ['usr/sbin/rc'], changed
assert added == ['usr/lib/systemd/system/asus-haveged.service', 'usr/libexec/leon-haveged-check'], added
assert not before.keys() - after.keys()
assert sum(n.endswith('.ko') for n in before) == 182
(r / 'evidence/production-staging.json').write_text(json.dumps({
    'parent': parent.name, 'changed': changed, 'added': added,
    'kernel_changed': False, 'modules_unchanged': 182,
    'init_and_trial_monitor_unchanged': True, 'libovpn_and_notify_shim_unchanged': True,
    'rc_sha256': sha(root / 'usr/sbin/rc'),
    'router_modified': False, 'firmware_commit_performed': False,
}, indent=2) + '\n')

# The parent scripts derive the checkpoint root from their own location.
# Keep their exact copies in this checkpoint so archived guests can be rebuilt.
for name in ('common.py', 'run-qemu.py', 'rehearsal-init.sh', 'pack-rootfs.py', 'fitlib.py'):
    shutil.copy2(parent / 'scripts' / name, r / 'scripts' / name)
for p in (parent / 'build/probes').iterdir():
    shutil.copy2(p, r / 'build/probes' / p.name)
text = (parent / 'tests/compat-check.sh').read_text()
needle = 'systemctl start asus-rc-real-power.service'
assert text.count(needle) == 1
text = text.replace(needle, '/usr/libexec/service-check.sh\n' + needle)
(r / 'tests/compat-check.sh').write_text(text)
p = r / 'build/probes/service-check.sh'
shutil.copy2(r / 'tests/service-check.sh', p); p.chmod(0o755)
print('PRODUCTION_DELTA_STAGED', changed, added)
