#!/usr/bin/env python3
"""Rebuild SSH ownership using the recorded BE98 flags and retained rc objects."""
from pathlib import Path
import difflib
import json
import os
import shutil
import subprocess
from common import sha

r = Path(__file__).resolve().parents[1]; w = r.parent
p = w/'rmerlin-integration-20260916'
original = p/'source-tree/release/src/router/rc'
src = r/'src'; out = r/'build/rc'; probes = r/'build/probes'
prior = w/'systemd-rc-next-20260917'
t = json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env = dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir'])
commands = []
def run(cmd, name):
    commands.append(cmd)
    with (r/'evidence'/f'{name}.log').open('w') as log:
        result = subprocess.run(cmd, cwd=original, env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print((r/'evidence'/f'{name}.log').read_text()[-6000:])
        raise SystemExit(result.returncode)

patch = ''
for name in ('ssh.c','rc-services.c','rc-services.h'):
    before=(r/'saved-inputs'/name).read_text(); after=(src/name).read_text()
    path='release/src/router/rc/'+name
    patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
(r/'patches/sshd-service.patch').write_text(patch)
templates=json.loads((p/'build/management-rc/compile-commands.json').read_text())
for name in ('ssh','rc-services'):
    cmd=next(c[:] for c in templates if str(original/(name+'.c')) in c)
    cmd[cmd.index(str(original/(name+'.c')))]=str(src/(name+'.c'))
    cmd[1:1]=['-I'+str(src),'-I'+str(original)]
    cmd[cmd.index('-o')+1]=str(out/(name+'.o'))
    cmd[cmd.index('-MF')+1]=str(out/(name+'.d'))
    run(cmd,'compile-'+name)
oldcommands=json.loads((prior/'evidence/rc-build.json').read_text())['commands']
link=next(c[:] for c in oldcommands if '-o' in c and c[c.index('-o')+1]==str(prior/'build/rc/rc'))
link[link.index('-o')+1]=str(out/'rc')
for name in ('ssh','rc-services'):
    index=next(i for i,x in enumerate(link) if x.endswith('/'+name+'.o'))
    link[index]=str(out/(name+'.o'))
run(link,'link-rc')
run([t['tools']+'strip','--strip-unneeded','-o',str(out/'rc.stripped'),str(out/'rc')],'strip-rc')
small=[t['cc'],'-std=gnu11','-O2','-g','-Wall','-Wextra','-Werror','-I'+str(src),'-frecord-gcc-switches','-Wl,--build-id=sha1']
bridge=[str(out/'rc-services.o'),str(src/'rc-manager.c'),str(src/'rc-client.c')]
for name,objects,wraps in (
    ('ssh-services-probe',[out/'ssh.o'],'leon_rc_managed'),
    ('services-probe',[prior/'build/rc/services.o'],'leon_rc_managed'),
    ('network-services-probe',[prior/'build/rc/services.o',prior/'build/rc/ntpd.o'],'leon_rc_managed,start_ddns,stop_ddns,start_stubby,stop_stubby')):
    flags='-Wl,--gc-sections'+''.join(',--wrap='+s for s in wraps.split(','))
    run(small+[str(r/'tests'/(name+'.c')),*map(str,objects),*bridge,flags,'-o',str(probes/name)],'build-'+name)
for source in (prior/'build/probes').iterdir():
    if not (probes/source.name).exists():shutil.copy2(source,probes/source.name)
native=[str(w/'systemd-features-20260917/build/cc'),'-Oz','-flto','-Wall','-Wextra','-Werror','-D_FORTIFY_SOURCE=2','-fstack-protector-strong','-frecord-gcc-switches','-Wl,--build-id=sha1','-Wl,-z,relro,-z,now',str(src/'leon-service-exec.c'),'-o',str(out/'leon-service-exec')]
run(native,'build-service-exec')
run(['strip','--strip-unneeded',str(out/'leon-service-exec')],'strip-service-exec')
(r/'evidence/rc-build.json').write_text(json.dumps({'commands':commands,'cwd':str(original),'retained_objects':{str(Path(x).relative_to(w)):sha(x) for x in link if x.endswith('.o') and Path(x).parent!=out},'rc_sha256':sha(out/'rc.stripped'),'helper_sha256':sha(out/'leon-service-exec'),'retains_a3_ipsec_fix':True},indent=2)+'\n')
print('RC_SSH_AND_REGRESSION_PROBES_BUILT')
