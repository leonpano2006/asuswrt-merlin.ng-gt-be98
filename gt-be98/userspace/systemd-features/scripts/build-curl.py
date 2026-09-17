#!/usr/bin/env python3
import os,json,subprocess,shutil,hashlib,time
from pathlib import Path
r=Path(__file__).resolve().parents[1];src=r/'sources/curl-8.22.0';b=r/'build/curl-hidden';b.mkdir(exist_ok=False)
sdk=r/'sdk';lib=sdk/'usr/lib/aarch64-linux-gnu'
env=dict(os.environ,CC=str(r/'build/cc'),CFLAGS='-Os -Oz -g -flto=4 -frecord-gcc-switches -fstack-protector-strong',LDFLAGS='-flto=4 -Wl,--build-id=sha1,-z,relro,-z,now',LC_ALL='C',PKG_CONFIG_SYSROOT_DIR=str(sdk),PKG_CONFIG_LIBDIR=str(lib/'pkgconfig'))
env.pop('LD_LIBRARY_PATH',None);env.pop('PKG_CONFIG_PATH',None)
commands=[[str(src/'configure'),'--build=aarch64-build-linux-gnu','--host=aarch64-linux-gnu','--prefix=/usr','--libdir=/usr/lib/aarch64-linux-gnu','--enable-shared','--disable-static','--disable-manual','--disable-docs','--disable-ldap','--disable-ldaps','--without-libpsl','--without-libidn2','--without-libssh2','--without-librtmp','--without-nghttp2','--without-nghttp3','--without-ngtcp2','--without-quiche','--without-brotli','--with-openssl','--with-zlib','--with-zstd','--with-ca-bundle=/etc/ssl/certs/ca-certificates.crt','--with-ca-path=/etc/ssl/certs'],['make','-j4'],['make','install','DESTDIR='+str(r/'build/curl-hidden-install')]]
(r/'evidence/curl-commands.json').write_text(json.dumps({'commands':commands,'env':{k:env[k] for k in ['CC','CFLAGS','LDFLAGS','PKG_CONFIG_SYSROOT_DIR','PKG_CONFIG_LIBDIR']},'cwd':str(b)},indent=2)+'\n')
for i,cmd in enumerate(commands):
 with (r/'evidence'/f'curl-hidden-{i}.log').open('w') as log:ret=subprocess.run(cmd,cwd=b,env=env,stdout=log,stderr=subprocess.STDOUT)
 if ret.returncode:print((r/'evidence'/f'curl-hidden-{i}.log').read_text()[-5000:]);raise SystemExit(ret.returncode)
assert 'CURL_EXTERN_SYMBOL' in (b/'lib/curl_config.h').read_text()
assert 'fvisibility=hidden' in (b/'lib/Makefile').read_text()
install=r/'build/curl-hidden-install';shutil.copytree(install/'usr/include/curl',sdk/'usr/include/curl',dirs_exist_ok=True)
for p in (install/'usr/lib/aarch64-linux-gnu').glob('libcurl.so*'):
 for dst in [lib/p.name,r/'overlay/usr/lib/aarch64-linux-gnu'/p.name]:
  dst.parent.mkdir(parents=True,exist_ok=True)
  if dst.exists() or dst.is_symlink():dst.unlink()
  if p.is_symlink():dst.symlink_to(p.readlink())
  else:
   shutil.copy2(p,dst);subprocess.run(['aarch64-linux-gnu-strip','--strip-unneeded',str(dst)],check=True)
# Build-only unversioned link is not needed in production.
(r/'overlay/usr/lib/aarch64-linux-gnu/libcurl.so').unlink()
shutil.copy2(install/'usr/lib/aarch64-linux-gnu/pkgconfig/libcurl.pc',lib/'pkgconfig/libcurl.pc')
version=subprocess.check_output([str(r/'build/run-target'),str(install/'usr/bin/curl'),'--version'],text=True)
record={'version':version,'files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (r/'overlay/usr/lib/aarch64-linux-gnu').glob('libcurl.so*') if not p.is_symlink()}}
(r/'evidence/curl-built.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
