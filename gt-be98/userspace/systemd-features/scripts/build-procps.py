#!/usr/bin/env python3
import os,json,subprocess,shutil,hashlib,time
from pathlib import Path
r=Path(__file__).resolve().parents[1];src=r/'sources/procps-ng-4.0.7';b=r/'build/procps';b.mkdir(exist_ok=False)
env=dict(os.environ,CC=str(r/'build/cc'),CFLAGS='-Oz -g -flto=4 -frecord-gcc-switches -fstack-protector-strong',LDFLAGS='-flto=4 -Wl,--build-id=sha1,-z,relro,-z,now',LC_ALL='C',PKG_CONFIG_SYSROOT_DIR=str(r/'sdk'),PKG_CONFIG_LIBDIR=str(r/'sdk/usr/lib/aarch64-linux-gnu/pkgconfig'))
env.pop('LD_LIBRARY_PATH',None);env.pop('PKG_CONFIG_PATH',None)
commands=[[str(src/'configure'),'--build=aarch64-build-linux-gnu','--host=aarch64-linux-gnu','--prefix=/usr','--sbindir=/usr/sbin','--disable-nls','--without-ncurses','--without-systemd','--without-elogind'],['make','-j4','src/sysctl']]
(r/'evidence/procps-commands.json').write_text(json.dumps({'commands':commands,'env':{k:env[k] for k in ['CC','CFLAGS','LDFLAGS']},'cwd':str(b)},indent=2)+'\n')
for i,cmd in enumerate(commands):
 with (r/'evidence'/f'procps-{i}.log').open('w') as log:
  ret=subprocess.run(cmd,cwd=b,env=env,stdout=log,stderr=subprocess.STDOUT)
 if ret.returncode:print((r/'evidence'/f'procps-{i}.log').read_text()[-4000:]);raise SystemExit(ret.returncode)
out=r/'overlay/usr/sbin/sysctl';out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(b/'src/sysctl',out)
subprocess.run(['aarch64-linux-gnu-strip','--strip-unneeded',str(out)],check=True)
version=subprocess.check_output([str(r/'build/run-target'),str(out),'--version'],text=True)
record={'version':version.strip(),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'needed':subprocess.check_output(['readelf','-d',str(out)],text=True)}
(r/'evidence/procps-built.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
