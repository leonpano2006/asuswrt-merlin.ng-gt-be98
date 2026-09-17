#!/usr/bin/env python3
"""Keep iperf 3.21's existing features, reuse the internal glibc runtime."""
import json, os, shutil, subprocess
from pathlib import Path
from common import sha
r=Path(__file__).resolve().parents[1]
src=r/'sources/iperf-3.21';build=r/'build/iperf-dynamic'
assert not build.exists()
if not src.exists():
    shutil.copytree('/home/leonpano/gcc16-a53/build/iperf-3.21',src,symlinks=True)
    with (r/'evidence/iperf-distclean.log').open('w') as log:
        subprocess.run(['make','distclean'],cwd=src,stdout=log,stderr=subprocess.STDOUT,check=True)
build.mkdir()
env=dict(os.environ,CC=str(r/'build/cc'),CFLAGS='-Oz -g -flto=4 -frecord-gcc-switches -fstack-protector-strong',
         LDFLAGS='-flto=4 -Wl,--build-id=sha1,-z,relro,-z,now',LC_ALL='C')
env.pop('LD_LIBRARY_PATH',None)
cmds=[[str(src/'configure'),'--prefix=/usr','--build=aarch64-build-linux-gnu',
       '--host=aarch64-linux-gnu','--without-openssl','--disable-shared'],
      ['make','-j4']]
(r/'evidence/iperf-commands.json').write_text(json.dumps({'commands':cmds,'cwd':str(build),
    'cflags':env['CFLAGS'],'ldflags':env['LDFLAGS']},indent=2)+'\n')
for i,cmd in enumerate(cmds):
    logpath=r/'evidence'/f'iperf-{i}.log'
    with logpath.open('w') as log: ret=subprocess.run(cmd,cwd=build,env=env,stdout=log,stderr=subprocess.STDOUT)
    if ret.returncode: print(logpath.read_text()[-5000:]);raise SystemExit(ret.returncode)
out=r/'size-overlay/usr/bin/iperf3';out.parent.mkdir(exist_ok=True,parents=True)
shutil.copy2(build/'src/iperf3',out)
subprocess.run(['aarch64-linux-gnu-strip','--strip-unneeded',str(out)],check=True)
assert 'Requesting program interpreter: /lib/ld-linux-aarch64.so.1' in subprocess.check_output(['readelf','-l',str(out)],text=True)
version=subprocess.check_output([str(r/'build/run-target'),str(out),'--version'],text=True)
old=subprocess.check_output([str(r.parent/'armhf-release-20260917/build/rootfs/usr/bin/iperf3'),'--version'],text=True)
assert version==old,(version,old)
record={'version':version,'same_optional_features':True,'bytes':out.stat().st_size,'sha256':sha(out)}
(r/'evidence/iperf-built.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
