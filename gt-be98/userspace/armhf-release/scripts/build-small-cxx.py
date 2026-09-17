#!/usr/bin/env python3
"""Rebuild existing-version C++ runtime for size, retaining ABI configuration."""
import argparse,json,os,shlex,subprocess,time,shutil,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('abi',choices=['aarch64','armel']);p.add_argument('--optimization',choices=['oz','oz-lto','oz-thumb'],default='oz');a=p.parse_args()
r=Path(__file__).resolve().parents[1];w=r.parent;old=w/'a53-runtimes-20260916'
cfg=json.loads((old/'configs/build-targets.json').read_text())[a.abi]
label=a.abi+'-'+a.optimization
parent=r/'build'/label;parent.mkdir(parents=True,exist_ok=True)
libgcc=old/'builds'/a.abi/'gcc-runtime'/cfg['triplet']/'libgcc'
(parent/'libgcc').symlink_to(libgcc)
obj=parent/'libstdc++-v3';obj.mkdir()
wrapper=obj/'cc';wrapper.write_text((libgcc.parent/'libstdc++-v3/runtime-cc').read_text());wrapper.chmod(0o755)
env=dict(os.environ,LC_ALL='C');env.pop('LD_LIBRARY_PATH',None)
if cfg['host_library_dir']:env['LD_LIBRARY_PATH']=cfg['host_library_dir']
env['PATH']=str(Path(cfg['tools']).parent)+':'+env['PATH']
assert a.optimization!='oz-thumb' or a.abi=='armel'
flags='-Oz -g -frecord-gcc-switches'+(' -flto=4' if a.optimization=='oz-lto' else '')+(' -mthumb' if a.optimization=='oz-thumb' else '')
env.update(CC=str(wrapper),CXX=str(wrapper)+' -shared-libgcc -nostdinc++',CFLAGS=flags,CXXFLAGS=flags,LDFLAGS=('-flto=4 ' if a.optimization=='oz-lto' else '')+'-Wl,--build-id=sha1,-z,relro,-z,now')
for k in ['AR','AS','LD','NM','RANLIB','STRIP']:env[k]=cfg['tools']+k.lower()
plugin=w/('gcc162-usb/obj/gcc/liblto_plugin.so' if a.abi=='aarch64' else 'armel-multiarch-20260915/toolchain/usr/libexec/gcc-cross/arm-linux-gnueabi/15/liblto_plugin.so')
for k in ['AR','RANLIB']:env[k]+=' --plugin='+str(plugin)
source=w/'gcc162-usb/gcc-16.2.0' if a.abi=='aarch64' else old/'sources/gcc-15.2.0'
commands=[[str(source/'libstdc++-v3/configure'),'--build=aarch64-build-linux-gnu','--host='+cfg['triplet'],'--target='+cfg['triplet'],'--prefix=/usr','--libdir=/usr/lib/'+cfg['triplet'],'--with-gxx-include-dir=/usr/include/c++/'+cfg['compiler_version'],'--disable-multilib','--enable-shared','--enable-static','--disable-nls','--disable-libstdcxx-pch','--enable-clocale=gnu','--enable-c99','--enable-libstdcxx-time=yes','--enable-libstdcxx-threads','--enable-libstdcxx-dual-abi','--with-default-libstdcxx-abi=new','--enable-symvers=gnu','--enable-tls','--disable-werror'],['make','-j4']]
(r/'evidence'/f'{label}-commands.json').write_text(json.dumps({'cwd':str(obj),'commands':commands,'env':{k:env[k] for k in ['CC','CXX','CFLAGS','CXXFLAGS','LDFLAGS','AR','RANLIB']}},indent=2)+'\n')
start=time.monotonic()
for i,c in enumerate(commands):
 print(a.abi,'STEP',i,flush=True)
 with (r/'evidence'/f'{label}-build-{i}.log').open('w') as log:
  rc=subprocess.run(c,cwd=obj,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
 if rc:print((r/'evidence'/f'{label}-build-{i}.log').read_text()[-5000:]);raise SystemExit(rc)
assert '#define _GLIBCXX_HAS_GTHREADS 1' in (obj/'config.h').read_text()
built=(obj/'src/.libs/libstdc++.so.6').resolve(strict=True)
out=r/'overlay/usr/lib'/cfg['triplet']/built.name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(built,out)
subprocess.run([env['STRIP'],'--strip-unneeded',str(out)],env=env,check=True);out.chmod(0o755)
record={'abi':a.abi,'optimization':a.optimization,'version':cfg['compiler_version'],'path':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'seconds':time.monotonic()-start,'tested':False}
(r/'evidence'/f'{a.abi}-built.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
