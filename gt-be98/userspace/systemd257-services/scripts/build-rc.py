#!/usr/bin/env python3
"""Rebuild only changed rc objects; retain the published a3 IPsec correction."""
from pathlib import Path
import difflib
import json
import os
import shutil
import subprocess
from common import sha

r=Path(__file__).resolve().parents[1];w=r.parent
p=w/'rmerlin-integration-20260916';src=p/'source-tree/release/src/router/rc'
t=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env=dict(os.environ,LD_LIBRARY_PATH=t['host_library_dir'])
out=r/'build/rc';out.mkdir(exist_ok=True)
probes=r/'build/probes';probes.mkdir(exist_ok=True)
commands=[]
def run(cmd,name):
    commands.append(cmd)
    with (r/'evidence'/f'{name}.log').open('w') as log:
        result=subprocess.run(cmd,cwd=src,env=env,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:
        print((r/'evidence'/f'{name}.log').read_text()[-6000:]);raise SystemExit(result.returncode)

patch=''
for name in ('services.c','rc-services.c','rc-services.h'):
    after=(src/name).read_text();before=(r/'saved-inputs'/name).read_text()
    shutil.copy2(src/name,r/'src'/name)
    path='release/src/router/rc/'+name
    patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
(r/'patches/cron-infosvr-services.patch').write_text(patch)
prior=json.loads((p/'build/management-rc/compile-commands.json').read_text())
for name in ('services','rc-services'):
    cmd=next(c[:] for c in prior if str(src/(name+'.c')) in c)
    cmd[cmd.index('-o')+1]=str(out/(name+'.o'))
    cmd[cmd.index('-MF')+1]=str(out/(name+'.d'))
    run(cmd,'compile-'+name)
link=json.loads((p/'build/management-rc/link-command.json').read_text())
link[link.index('-o')+1]=str(out/'rc')
for name in ('services','rc-services'):
    link[link.index(str(p/'build/management-rc'/(name+'.o')))]=str(out/(name+'.o'))
link[link.index(str(p/'build/management-rc/rc_ipsec.o'))]=str(w/'rmerlin-ipsec-fix-20260916/build/rc_ipsec.o')
run(link,'link-rc')
run([t['tools']+'strip','--strip-unneeded','-o',str(out/'rc.stripped'),str(out/'rc')],'strip-rc')
(out/'rc.stripped').chmod(0o755)
small=[t['cc'],'-std=gnu11','-O2','-g','-Wall','-Wextra','-Werror','-I'+str(src),
       '-frecord-gcc-switches','-Wl,--build-id=sha1']
run(small+[str(r/'tests/services-probe.c'),str(out/'services.o'),str(src/'rc-services.c'),
    str(src/'rc-manager.c'),str(src/'rc-client.c'),'-Wl,--gc-sections,--wrap=leon_rc_managed',
    '-o',str(probes/'services-probe')],'build-services-probe')
run(small+[str(r/'tests/infosvr-mock.c'),'-o',str(probes/'infosvr-mock')],'build-infosvr-mock')
(r/'evidence/rc-build.json').write_text(json.dumps({'commands':commands,'retained_objects':
    {str(Path(x).relative_to(w)):sha(x) for x in link if x.endswith('.o') and Path(x).parent!=out},
    'rc_sha256':sha(out/'rc.stripped'),'retains_a3_ipsec_fix':True},indent=2)+'\n')
print('RC_AND_SERVICE_PROBES_BUILT')
