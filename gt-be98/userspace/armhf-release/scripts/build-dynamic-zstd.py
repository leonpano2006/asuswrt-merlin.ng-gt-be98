#!/usr/bin/env python3
"""Build the full upstream CLI against the already shipped zstd/zlib DSOs."""
import hashlib,json,shutil,subprocess
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent
build=r/'build/zstd-dynamic-full';build.mkdir(exist_ok=False)
src=build/'source';shutil.copytree('/home/leonpano/gcc16-a53/build/zstd-1.5.7',src,symlinks=True)
inc=build/'include';inc.mkdir();lib=build/'lib';lib.mkdir()
for n in ['zlib.h','zconf.h']:shutil.copy2(Path('/home/leonpano/gcc16-a53/build/zlib-1.3.2')/n,inc/n)
root=r/'build/rootfs';dso=root/'usr/lib/aarch64-linux-gnu'
for name,target in [('libzstd.so','libzstd.so.1.5.7'),('libz.so','libz.so.1.3.2')]:
 (lib/name).symlink_to(dso/target)
cmd=['make','-C',str(src/'programs'),'-j8','zstd-dll',
 'CC='+str(w/'userspace-refresh-20260917/build/cc'),
 'CFLAGS=-Oz -g -frecord-gcc-switches -fstack-protector-strong -I'+str(inc),
 'LDFLAGS=-L'+str(lib)+' -Wl,--build-id=sha1,-z,relro,-z,now',
 'HAVE_ZLIB=1','HAVE_LZMA=0','HAVE_LZ4=0','BACKTRACE=0']
with (r/'evidence/zstd-build.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
out=build/'zstd';shutil.copy2(src/'programs/zstd',out)
subprocess.run(['aarch64-linux-gnu-strip','--strip-unneeded',str(out)],check=True)
sdk=w/'userspace-refresh-20260917/sdk'
prefix=[str(sdk/'lib/ld-linux-aarch64.so.1'),'--library-path',str(dso)]
old=root/'usr/bin/zstd'
versions={label:subprocess.check_output(prefix+[str(p),'-V','-vv'],stderr=subprocess.STDOUT,text=True) for label,p in [('old',old),('new',out)]}
record={'command':cmd,'versions':versions,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bytes':out.stat().st_size,
 'needed':subprocess.check_output(['readelf','-d',str(out)],text=True)}
(r/'evidence/zstd-build.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
