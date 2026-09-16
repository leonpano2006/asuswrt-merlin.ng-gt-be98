#!/usr/bin/env python3
"""Build standalone upstream daemons with GCC 15/A53 and isolated TLS 3.5."""
from pathlib import Path
import argparse, hashlib, json, os, shlex, shutil, subprocess, time
r=Path(__file__).resolve().parents[1]; w=r.parent
router=r/'source-tree/release/src/router'
old=w/'leon-cgroup-20260915/archive/worktree/release/src/router'
t=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
p=argparse.ArgumentParser(); p.add_argument('package', choices=['openvpn','tor','haveged','strongswan','inadyn']); p.add_argument('--reconfigure',action='store_true'); a=p.parse_args()
source=router/a.package; build=r/'build'/('package-'+a.package); build.mkdir(exist_ok=True)
stage=r/'build'/('stage-'+a.package); empty=r/'build/empty-pkgconfig'; empty.mkdir(exist_ok=True)
ssl=r/'build/openssl-armel'; sslsource=r/'sources/release/src/router/openssl-3.5'
flags='-Os -g -frecord-gcc-switches -ffunction-sections -fdata-sections -fstack-protector-strong -std=gnu11'
env=dict(os.environ, PATH=str(r/'build/host-tools/usr/bin')+':'+os.environ['PATH'], LD_LIBRARY_PATH=t['host_library_dir'], CC=t['cc'], AR=t['tools']+'ar', RANLIB=t['tools']+'ranlib', NM=t['tools']+'nm', STRIP=t['tools']+'strip',
 CFLAGS=flags, LDFLAGS='-Wl,--gc-sections,--build-id=sha1', PKG_CONFIG_LIBDIR=str(empty), PKG_CONFIG_PATH='')
commands=[]; start=time.monotonic()
def run(cmd, label, cwd=build):
 commands.append({'cwd':str(cwd),'argv':cmd})
 (build/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 with (build/(label+'.log')).open('w') as log: result=subprocess.run(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
 if result.returncode:
  print((build/(label+'.log')).read_text()[-6000:],flush=True); raise SystemExit(result.returncode)
common=['--host=arm-linux-gnueabi','--build=aarch64-linux-gnu','--prefix=/usr','--bindir=/usr/sbin','--libdir=/usr/lib/arm-linux-gnueabi']
if a.package=='openvpn':
 env.update(OPENSSL_CFLAGS=f'-I{ssl}/include -I{sslsource}/include', OPENSSL_LIBS=f'-L{ssl} -lssl -lcrypto',
   LIBPAM_CFLAGS=f'-I{old}/openpam/include', LIBPAM_LIBS=f'-L{w}/systemd-service-split-20260916/build/production-rootfs/usr/lib/arm-linux-gnueabi -l:libpam.so.2',
   LZO_CFLAGS=f'-I{old}/lzo-2.10/include', LZO_LIBS=f'-L{old}/lzo-2.10/src/.libs -llzo2',
   LZ4_CFLAGS=f'-I{old}/lz4/lib', LZ4_LIBS=f'-L{old}/lz4/lib -llz4',
   LIBCAPNG_CFLAGS=f'-I{old}/libcap-ng/src', LIBCAPNG_LIBS=f'-L{old}/libcap-ng/src/.libs -lcap-ng',
   CFLAGS=flags+' -DASUSWRT', LDFLAGS=env['LDFLAGS']+f' -lpthread -ldl -L{old}/zlib -lz', IPROUTE='/usr/sbin/ip')
 run(['sh', 'autogen.sh'],'autoreconf',source)
 options=['--disable-debug','--enable-management','--disable-small','--disable-selinux','--disable-dco','--enable-plugin-auth-pam','ac_cv_lib_resolv_gethostbyname=no','--enable-iproute2']
 outputs=['src/openvpn/.libs/openvpn','src/plugins/auth-pam/.libs/openvpn-plugin-auth-pam.so']
elif a.package=='tor':
 env.update(CFLAGS=flags+f' -I{ssl}/include -I{sslsource}/include -I{old}/libevent-2.0.21/include -I{old}/libevent-2.0.21 -I{old}/zlib',
   LDFLAGS=env['LDFLAGS']+f' -L{ssl} -L{old}/libevent-2.0.21/.libs -L{old}/zlib')
 options=[f'--with-libevent-dir={old}/libevent-2.0.21',f'--with-openssl-dir={ssl}',f'--with-zlib-dir={old}/zlib','--disable-asciidoc','--disable-manpage','--disable-html-manual','--disable-tool-name-check','--disable-unittests','--disable-lzma','--disable-zstd','--disable-seccomp','--disable-libscrypt']
 outputs=['src/app/tor']
elif a.package=='inadyn':
 run(['autoreconf','-if'],'autoreconf',source)
 parent=w/'systemd-service-split-20260916/build/production-rootfs/usr/lib/arm-linux-gnueabi'
 h=old.parents[1]/'src-rt-5.04behnd.4916'
 includes=h/'bcmdrivers/broadcom/net/wl/bcm96813/main/src/include'
 env.update(CFLAGS=flags+f' -DASUSWRT -DHND_ROUTER -DGTBE98 -DUSE_IPV6 -DASUSWRT_LE -DRTCONFIG_ASUSDDNS_ACCOUNT_BASE -I{router}/shared -I{old}/shared -I{includes} -I{old}/libconfuse/src -I{old}/openssl-1.1/include -Wno-error=implicit-function-declaration -Wno-error=incompatible-pointer-types -Wno-error=int-conversion',
  LDFLAGS=env['LDFLAGS']+f' -L{r}/build/management-libs -L{parent} -Wl,-rpath-link,{parent}',
  LIBS='-lnvram -lshared -ldl',confuse_CFLAGS=f'-I{old}/libconfuse/src',confuse_LIBS=f'-L{old}/libconfuse/src/.libs -lconfuse',
  OpenSSL_CFLAGS=f'-I{old}/openssl-1.1/include',OpenSSL_LIBS=f'-L{parent} -lcrypto -lssl -lpthread')
 options=['--sysconfdir=/etc','--localstatedir=/var','--enable-openssl']
 outputs=['src/inadyn']
elif a.package=='strongswan':
 run(['autoreconf','-if'],'autoreconf',source)
 env.update(CFLAGS=flags+f' -DHND_ROUTER -I{ssl}/include -I{sslsource}/include -Wno-error=incompatible-pointer-types -Wno-error=int-conversion -Wno-error=implicit-function-declaration',
   LDFLAGS=env['LDFLAGS']+f' -L{ssl}', LIBS='-lssl -lcrypto -lpthread -ldl -lm')
 options=['--sysconfdir=/etc','--localstatedir=/var','--libexecdir=/usr/lib/arm-linux-gnueabi','--enable-silent-rules','--disable-gmp','--enable-openssl','--enable-acert','--enable-agent','--enable-md4','--enable-eap-identity','--enable-eap-md5','--enable-eap-mschapv2','--enable-eap-tls','--enable-eap-peap','--enable-stroke','--enable-aes','--enable-des','--enable-fips-prf','--enable-gcm','--enable-curve25519','--enable-hmac','--enable-md5','--enable-sha1','--enable-sha2','--enable-cmd','--enable-libipsec','--enable-shared','--disable-static','--with-ipsecdir=/usr/lib/arm-linux-gnueabi/ipsec','--with-strongswan-conf=/etc/strongswan.conf','--with-user=admin']
 outputs=['src/charon/.libs/charon','src/libstrongswan/.libs/libstrongswan.so.0.0.0']
else:
 run(['autoreconf','-if'],'autoreconf',source)
 options=['--enable-static','--disable-shared','--enable-daemon','--disable-tune','--disable-olt']
 outputs=['src/haveged']
(build/'environment.json').write_text(json.dumps({k:v for k,v in env.items() if k not in os.environ or os.environ[k]!=v},indent=2)+'\n')
if a.reconfigure or not (build/'Makefile').exists(): run([str(source/'configure')]+common+options,'configure')
if a.package=='tor' and a.reconfigure: run(['make','clean'],'clean-lto')
if a.package=='openvpn' and a.reconfigure:
 run(['make','-C','src/plugins/auth-pam','clean'],'clean-pam')
if a.package=='strongswan' and a.reconfigure:
 for name in ('src/starter/keywords.h','src/starter/keywords.c'): (build/name).unlink(missing_ok=True)
run(['make','-j8']+(['GPERF='+shutil.which('gperf',path=env['PATH'])] if a.package=='strongswan' else []),'make')
if a.package=='strongswan': run(['make','DESTDIR='+str(stage),'install'],'install')
record={'package':a.package,'seconds':round(time.monotonic()-start,2),'compiler':t,'files':{name:{'sha256':hashlib.sha256((build/name).read_bytes()).hexdigest(),'bytes':(build/name).stat().st_size} for name in outputs}}
(build/'result.json').write_text(json.dumps(record,indent=2)+'\n'); print(json.dumps(record,indent=2),flush=True)
