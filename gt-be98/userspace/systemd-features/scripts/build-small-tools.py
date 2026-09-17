#!/usr/bin/env python3
"""Rebuild same-version Bash/coreutils with size optimization; retain features."""
import argparse,json,os,subprocess,shutil,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('name',choices=['bash','coreutils']);p.add_argument('--resume',action='store_true');a=p.parse_args()
r=Path(__file__).resolve().parents[1];w=r.parent;version={'bash':'5.3','coreutils':'9.11'}[a.name]
src=r/'sources'/f'{a.name}-{version}';
if not a.resume:
 if not src.exists():
  shutil.copytree(Path('/home/leonpano/gcc16-a53/build')/src.name,src,symlinks=True)
  with (r/'evidence'/f'{a.name}-distclean.log').open('w') as log:subprocess.run(['make','distclean'],cwd=src,stdout=log,stderr=subprocess.STDOUT,check=True)
 assert not (src/'Makefile').exists(), 'Use the clean source copy saved with this checkpoint'
b=r/'build'/f'{a.name}-oz';b.mkdir(exist_ok=a.resume);sdk=r/'sdk';lib=sdk/'usr/lib/aarch64-linux-gnu'
if a.name=='bash':
 old=w/'armhf-release-20260917/build/rootfs/usr/lib/aarch64-linux-gnu'
 for srcp in old.glob('libtinfo.so*'):
  out=lib/srcp.name
  if out.is_symlink() or out.exists():out.unlink()
  if srcp.is_symlink():out.symlink_to(srcp.readlink())
  else:shutil.copy2(srcp,out)
 link=lib/'libtinfo.so'
 if link.exists() or link.is_symlink():link.unlink()
 link.symlink_to('libtinfo.so.6')
env=dict(os.environ,CC=str(r/'build/cc'),CFLAGS='-Oz -g -flto=4 -frecord-gcc-switches -fstack-protector-strong',LDFLAGS='-flto=4 -Wl,--build-id=sha1,-z,relro,-z,now',LC_ALL='C',PKG_CONFIG_SYSROOT_DIR=str(sdk),PKG_CONFIG_LIBDIR=str(lib/'pkgconfig'),FORCE_UNSAFE_CONFIGURE='1')
env.pop('LD_LIBRARY_PATH',None);env.pop('PKG_CONFIG_PATH',None)
args=['--without-bash-malloc'] if a.name=='bash' else ['--enable-single-binary=symlinks','--disable-nls']
commands=[[str(src/'configure'),'--build=aarch64-build-linux-gnu','--host=aarch64-linux-gnu','--prefix=/usr']+args,['make','-j4','bash' if a.name=='bash' else 'src/coreutils']]
if a.name=='coreutils':
 fragment=b/'leon-generated.mk';fragment.write_text('.PHONY: leon-generated\nleon-generated: $(BUILT_SOURCES)\n')
 commands.insert(1,['make','-j4','-f','Makefile','-f',str(fragment),'leon-generated'])
(r/'evidence'/f'{a.name}-commands.json').write_text(json.dumps({'commands':commands,'cwd':str(b),'flags':env['CFLAGS'],'ldflags':env['LDFLAGS']},indent=2)+'\n')
for i,cmd in enumerate(commands):
 if a.resume and i==0:continue
 with (r/'evidence'/f'{a.name}-{i}.log').open('w') as log:ret=subprocess.run(cmd,cwd=b,env=env,stdout=log,stderr=subprocess.STDOUT)
 if ret.returncode:print((r/'evidence'/f'{a.name}-{i}.log').read_text()[-4500:]);raise SystemExit(ret.returncode)
rel='usr/bin/bash' if a.name=='bash' else 'usr/gnu/bin/coreutils'
out=r/'size-overlay'/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(b/('bash' if a.name=='bash' else 'src/coreutils'),out)
subprocess.run(['aarch64-linux-gnu-strip','--strip-unneeded',str(out)],check=True)
version=subprocess.check_output([str(r/'build/run-target'),str(out),'--version'],text=True)
record={'name':a.name,'version':version,'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'flags':env['CFLAGS']}
(r/'evidence'/f'{a.name}-built.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
