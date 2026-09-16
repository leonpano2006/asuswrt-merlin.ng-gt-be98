#!/usr/bin/env python3
"""Preserve the configured DNSSEC/IGDv2 features with new userspace sources."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, time
r=Path(__file__).resolve().parents[1]; w=r.parent
router=r/'source-tree/release/src/router'; old=w/'leon-cgroup-20260915/archive/worktree/release/src/router'
parent=w/'systemd-service-split-20260916/build/production-rootfs/usr/lib/arm-linux-gnueabi'
t=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
p=argparse.ArgumentParser(); p.add_argument('package',choices=['dnsmasq','miniupnpd','miniupnpd-igdv2']); a=p.parse_args()
source=router/a.package; build=r/'build'/('package-'+a.package); build.mkdir(exist_ok=True)
env=dict(os.environ,LD_LIBRARY_PATH=t['host_library_dir'],CC=t['cc'],AR=t['tools']+'ar',RANLIB=t['tools']+'ranlib',NM=t['tools']+'nm',STRIP=t['tools']+'strip',PKG_CONFIG='false',ARCH='arm')
flags='-Os -g -frecord-gcc-switches -ffunction-sections -fdata-sections -fstack-protector-strong -std=gnu11'
ldflags='-Wl,--gc-sections,--build-id=sha1'
commands=[]; start=time.monotonic()
def run(cmd,label,cwd=source):
 commands.append({'cwd':str(cwd),'argv':cmd}); (build/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
 with (build/(label+'.log')).open('w') as log: result=subprocess.run(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
 if result.returncode: print((build/(label+'.log')).read_text()[-7000:],flush=True); raise SystemExit(result.returncode)
if a.package=='dnsmasq':
 opts='-DHAVE_BROKEN_RTC -DHAVE_LEASEFILE_EXPIRE -DNO_ID -DNO_AUTH -DNO_INOTIFY -DNO_DUMPFILE -DNO_GMP -DUSE_IPV6 -DHAVE_DNSSEC -DHAVE_DNSSEC_STATIC -DNO_GOST'
 run(['make','-j8','CC='+t['cc'],'BUILDDIR='+str(build),'CFLAGS='+flags,'COPTS='+opts,'LDFLAGS='+ldflags,
  'nettle_cflags=-I'+str(old/'nettle/include'),'nettle_libs='+str(old/'nettle/lib/libhogweed.a')+' '+str(old/'nettle/lib/libnettle.a')], 'make')
 output=build/'dnsmasq'
else:
 # configure consults the kernel interface in the same iptables release as production.
 iptables=old/'iptables-1.4.x'
 opts=['sh','configure','--vendorcfg','--leasefile','--portinuse','--iptablespath='+str(iptables),'--disable-pppconn']
 if a.package.endswith('igdv2'): opts+=['--ipv6','--igd2']
 run(opts,'configure')
 shutil.copy2(router/'shared/version.h',source/'version.h')
 run(['make','-j8','CC='+t['cc'],'AR='+t['tools']+'ar','IPTABLESPATH='+str(iptables),
  'EXTRACFLAGS='+flags+' -I'+str(old/'e2fsprogs/lib'),
  'LDFLAGS='+ldflags+' -L'+str(parent)+' -Wl,-rpath-link,'+str(parent),
  'LDLIBS=-Wl,--as-needed -luuid -lrt -lip4tc'+(' -lip6tc' if a.package.endswith('igdv2') else '')+' -lwlcsm'], 'make')
 output=build/'miniupnpd'; shutil.copy2(source/'miniupnpd',output)
record={'package':a.package,'seconds':round(time.monotonic()-start,2),'compiler':t,'output':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size}
(build/'result.json').write_text(json.dumps(record,indent=2)+'\n'); print(json.dumps(record,indent=2),flush=True)
