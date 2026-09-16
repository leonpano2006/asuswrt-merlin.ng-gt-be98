#!/usr/bin/env python3
from pathlib import Path
import json, os, shutil, subprocess
r=Path(__file__).resolve().parents[1]; w=r.parent; parent=w/'systemd-service-split-20260916'; trial=w/'systemd-trial3-20260916'
for name in ('tests','configs','build/probes','candidate'): (r/name).mkdir(parents=True,exist_ok=True)
for name in ('common.py','pack-rehearsal.py','rehearsal-init.sh','run-qemu.py','pack-rootfs.py','fitlib.py'):
 if not (r/'scripts'/name).exists():shutil.copy2(parent/'scripts'/name,r/'scripts'/name)
for p in (parent/'build/probes').iterdir():shutil.copy2(p,r/'build/probes'/p.name)
for name in ('compat-check.sh','service-check.sh','service-probe.c'):shutil.copy2(parent/'tests'/name,r/'tests'/name)
shutil.copy2(parent/'configs/fit-public.pem',r/'configs/fit-public.pem')
s=(r/'tests/compat-check.sh').read_text().replace('/usr/libexec/service-check.sh','/usr/libexec/service-check.sh\n/usr/libexec/upstream-check.sh');(r/'tests/compat-check.sh').write_text(s)
t=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']; env=dict(os.environ,LD_LIBRARY_PATH=t['host_library_dir'])
command=[t['cc'],'-std=gnu11','-O2','-g','-Wall','-Wextra','-Werror','-I'+str(r/'src'),'-frecord-gcc-switches','-Wl,--build-id=sha1',str(r/'tests/service-probe.c'),str(r/'build/management-rc/services.o'),str(r/'src/rc-services.c'),str(r/'src/rc-manager.c'),str(r/'src/rc-client.c'),'-Wl,--gc-sections,--wrap=leon_rc_managed','-o',str(r/'build/probes/service-probe')]
with (r/'evidence/service-probe-build.log').open('w') as log: subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
(r/'evidence/service-probe-build.json').write_text(json.dumps(command,indent=2)+'\n')
shutil.copy2(parent/'build/production-rootfs/usr/sbin/openssl',r/'build/probes/openssl-legacy')
shutil.copy2(r/'tests/upstream-check.sh',r/'build/probes/upstream-check.sh')
(r/'build/probes/upstream-check.sh').chmod(0o755)
subprocess.run([t['cc'],'-std=gnu11','-Os','-Wall','-Wextra','-Werror',str(r/'tests/dns-probe.c'),'-o',str(r/'build/probes/dns-probe')],env=env,check=True)
print('REBUILT_SERVICE_PROBE_FROM_NEW_SERVICES_OBJECT')
