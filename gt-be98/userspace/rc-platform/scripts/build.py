from pathlib import Path
import json,os,subprocess,difflib
from common import sha
r=Path(__file__).resolve().parents[1];w=r.parent;old=w/'systemd-rc-ssh-20260917'
o=w/'rmerlin-integration-20260916/source-tree/release/src/router/rc'
t=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env=dict(os.environ,LD_LIBRARY_PATH=t['host_library_dir']);out=r/'build/rc';commands=[]
def run(cmd,name):
 commands.append(cmd)
 with (r/'evidence'/f'{name}.log').open('w') as f:p=subprocess.run(cmd,cwd=o,env=env,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode:print((r/'evidence'/f'{name}.log').read_text()[-7000:]);raise SystemExit(p.returncode)
templates=json.loads((w/'rmerlin-integration-20260916/build/management-rc/compile-commands.json').read_text())
for name in ('services','usb','rc-services'):
 cmd=next(c[:] for c in templates if str(o/(name+'.c')) in c)
 cmd[cmd.index(str(o/(name+'.c')))]=str(r/'src'/(name+'.c'))
 cmd[1:1]=['-I'+str(r/'src'),'-I'+str(o)]
 cmd[cmd.index('-o')+1]=str(out/(name+'.o'));cmd[cmd.index('-MF')+1]=str(out/(name+'.d'))
 run(cmd,'compile-'+name)
link=next(c[:] for c in json.loads((old/'evidence/rc-build.json').read_text())['commands'] if '-o' in c and c[c.index('-o')+1]==str(old/'build/rc/rc'))
link[link.index('-o')+1]=str(out/'rc')
for name in ('services','usb','rc-services'):
 index=next(i for i,x in enumerate(link) if x.endswith('/'+name+'.o'));link[index]=str(out/(name+'.o'))
run(link,'link-rc');run([t['tools']+'strip','--strip-unneeded','-o',str(out/'rc.stripped'),str(out/'rc')],'strip-rc')
run([str(w/'systemd-features-20260917/build/cc'),'-Oz','-flto','-Wall','-Wextra','-Werror','-D_FORTIFY_SOURCE=2','-fstack-protector-strong','-frecord-gcc-switches','-Wl,--build-id=sha1','-Wl,-z,relro,-z,now',str(r/'src/leon-daemon-supervisor.c'),'-o',str(out/'leon-daemon-supervisor')],'build-supervisor')
run(['strip','--strip-unneeded',str(out/'leon-daemon-supervisor')],'strip-supervisor')
patch=''
for name in ('services.c','usb.c','rc-services.c','rc-services.h'):
 before=(r/'saved-inputs'/name).read_text();after=(r/'src'/name).read_text();path='release/src/router/rc/'+name
 patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
(r/'patches/platform-services.patch').write_text(patch)
(r/'evidence/rc-build.json').write_text(json.dumps({'commands':commands,'cwd':str(o),'retained_objects':{str(Path(x).relative_to(w)):sha(x) for x in link if x.endswith('.o') and Path(x).parent!=out},'rc_sha256':sha(out/'rc.stripped'),'helper_sha256':sha(out/'leon-daemon-supervisor')},indent=2)+'\n')
print('PLATFORM_RC_BUILT')
