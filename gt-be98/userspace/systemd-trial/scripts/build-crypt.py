#!/usr/bin/env python3
"""Replace obsolete glibc-private libcrypt dependencies with the compatible public ABI."""
from pathlib import Path
import json,os,subprocess
r=Path(__file__).resolve().parents[1];w=r.parent
target=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
source=w/'systemd-lab-20260916/sources/libxcrypt-4.4.38'
out=r/'build/libxcrypt';out.mkdir(exist_ok=True)
env=dict(os.environ,LD_LIBRARY_PATH=target['host_library_dir'],CC=target['cc'],
    CFLAGS='-Os -g -frecord-gcc-switches',LDFLAGS='-Wl,--build-id=sha1')
commands=[[str(source/'configure'),'--prefix=/usr','--libdir=/usr/lib/arm-linux-gnueabi',
    '--host=arm-linux-gnueabi','--build=aarch64-linux-gnu','--enable-obsolete-api=yes',
    '--disable-static','--disable-werror'],['make','-j4'],['make','DESTDIR='+str(r/'build/crypt-stage'),'install']]
(r/'evidence/crypt-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
with (r/'evidence/crypt-build.log').open('w') as log:
    for command in commands:subprocess.run(command,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
dest=r/'overlay/usr/lib/arm-linux-gnueabi/libcrypt.so.1'
subprocess.run([target['tools']+'strip','--strip-unneeded','-o',str(dest),str(r/'build/crypt-stage/usr/lib/arm-linux-gnueabi/libcrypt.so.1')],env=env,check=True)
print('ARMEL_LIBCRYPT_PUBLIC_ABI_BUILT',dest.stat().st_size)
