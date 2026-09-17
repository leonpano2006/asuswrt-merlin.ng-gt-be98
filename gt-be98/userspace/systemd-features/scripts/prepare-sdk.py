#!/usr/bin/env python3
import shutil,subprocess
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent;sdk=r/'sdk';old=w/'userspace-refresh-20260917'
assert not sdk.exists();subprocess.run(['cp','-a','--reflink=auto',str(old/'sdk'),str(sdk)],check=True)
for name in ['cc','run-target']:
 p=r/'build'/name;p.write_text((old/'build'/name).read_text().replace(str(old),str(r)));p.chmod(0o755)
lib=sdk/'usr/lib/aarch64-linux-gnu';inc=sdk/'usr/include';parent=w/'armhf-release-20260917/build/rootfs/usr/lib/aarch64-linux-gnu'
for pattern in ['libz.so*','libzstd.so*','libcrypto.so.4','libssl.so.4']:
 for p in parent.glob(pattern):
  out=lib/p.name
  if out.exists() or out.is_symlink():out.unlink()
  if p.is_symlink():out.symlink_to(p.readlink())
  else:shutil.copy2(p,out)
for name,target in [('libz.so','libz.so.1'),('libzstd.so','libzstd.so.1')]:
 out=lib/name
 if out.is_symlink() or out.exists():out.unlink()
 out.symlink_to(target)
for n in ['zlib.h','zconf.h']:shutil.copy2(Path('/home/leonpano/gcc16-a53/build/zlib-1.3.2')/n,inc/n)
for n in ['zstd.h','zstd_errors.h','zdict.h']:shutil.copy2(Path('/home/leonpano/gcc16-a53/build/zstd-1.5.7/lib')/n,inc/n)
for name,version,link in [('zlib','1.3.2','z'),('libzstd','1.5.7','zstd')]:
 (lib/'pkgconfig'/f'{name}.pc').write_text(f'prefix=/usr\nlibdir=${{prefix}}/lib/aarch64-linux-gnu\nincludedir=${{prefix}}/include\nName: {name}\nDescription: Existing GT-BE98 runtime\nVersion: {version}\nLibs: -L${{libdir}} -l{link}\nCflags: -I${{includedir}}\n')
p=r/'build/cc';text=p.read_text();gcc=w/'gcc162-usb/obj/gcc/xgcc'
text=text.replace('#!/bin/sh\n',f'#!/bin/sh\nif [ "$*" = "--help --verbose" ]; then\n exec {gcc} -B{gcc.parent}/ --help=common\nfi\n')
p.write_text(text)
print('SDK_READY')
