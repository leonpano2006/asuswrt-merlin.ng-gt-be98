#!/usr/bin/env python3
"""Compile three ABI shims plus an AArch64 broker and controller on the DGX."""
from pathlib import Path
import json,os,subprocess,hashlib
r=Path(__file__).resolve().parents[1];w=r.parent
targets=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())
commands=[];outputs={}
common=['-std=gnu11','-Os','-g','-Wall','-Wextra','-Werror','-frecord-gcc-switches','-Wl,--build-id=sha1','-I'+str(r/'src')]
def build(abi,name,sources,flags=()):
    t=targets[abi];env=dict(os.environ)
    if t['host_library_dir']:env['LD_LIBRARY_PATH']=t['host_library_dir']
    else:env.pop('LD_LIBRARY_PATH',None)
    out=r/'build'/abi/name;out.parent.mkdir(exist_ok=True)
    cmd=[t['cc']]+common+list(flags)+[str(r/'src'/s) for s in sources]+['-o',str(out)]
    commands.append(cmd)
    subprocess.run(cmd,env=env,check=True)
    return out
for abi,t in targets.items():
    out=build(abi,'libleon-rc-notify.so',['notify-compat.c','rc-client.c'],['-fPIC','-shared','-Wl,-soname,libleon-rc-notify.so','-ldl'])
    dest=r/'overlay/usr/lib'/t['triplet']/out.name;dest.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([t['tools']+'strip','--strip-unneeded','-o',str(dest),str(out)],check=True,
        env=dict(os.environ,**({'LD_LIBRARY_PATH':t['host_library_dir']} if t['host_library_dir'] else {})))
for name,source in [('leon-rc-broker','rc-broker.c'),('leon-rcctl','rcctl.c')]:
    out=build('aarch64',name,[source,'rc-client.c'])
    dest=r/('overlay/usr/libexec' if name.endswith('broker') else 'overlay/usr/sbin')/name
    dest.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['/usr/bin/aarch64-linux-gnu-strip','--strip-unneeded','-o',str(dest),str(out)],check=True)
for p in (r/'overlay').rglob('*'):
    if p.is_file():outputs[str(p.relative_to(r/'overlay'))]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(r/'evidence/bridge-build.json').write_text(json.dumps({'commands':commands,'files':outputs},indent=2)+'\n')
print('BRIDGE_BUILT',len(outputs),sum(x['bytes'] for x in outputs.values()))
