#!/usr/bin/env python3
"""Stage a dual-TLS candidate without changing the kernel or vendor modules."""
from pathlib import Path
import json, os, re, shutil, subprocess, sys
r=Path(__file__).resolve().parents[1]; w=r.parent; parent=w/'systemd-service-split-20260916'
sys.path.insert(0,str(parent/'scripts')); from common import inventory,sha
root=r/'build/production-rootfs'; base=parent/'build/production-rootfs'; source=r/'source-tree/release/src/router'
t=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']; env=dict(os.environ,LD_LIBRARY_PATH=t['host_library_dir'])
assert not root.exists(); subprocess.run(['cp','-a','--reflink=auto',str(base),str(root)],check=True)
installed=[]
def copy(src,dest,elf=False,mode=None):
 p=root/dest;p.parent.mkdir(parents=True,exist_ok=True)
 if mode is None: mode=(base/dest).stat().st_mode & 0o777 if (base/dest).is_file() else 0o755
 if p.is_symlink(): p.unlink()
 if elf: subprocess.run([t['tools']+'strip','--strip-unneeded','-o',str(p),str(src)],env=env,check=True)
 else: shutil.copy2(src,p)
 p.chmod(mode); installed.append({'path':dest,'source':str(src),'sha256':sha(p),'elf':elf})
for c in ['rc','httpd','infosvr']: copy(r/'build'/('management-'+c)/c,'usr/sbin/'+c,True)
for c in ['shared','libovpn']:
 name='libshared.so' if c=='shared' else 'libovpn.so';copy(r/'build'/('management-'+c)/name,'usr/lib/arm-linux-gnueabi/'+name,True)
for c,out,name in [('openvpn','src/openvpn/.libs/openvpn','openvpn'),('tor','src/app/tor','Tor'),('haveged','src/haveged','haveged'),('dnsmasq','dnsmasq','dnsmasq'),('miniupnpd','miniupnpd','miniupnpd'),('miniupnpd-igdv2','miniupnpd','miniupnpd-igdv2'),('inadyn','src/inadyn','inadyn')]:copy(r/'build'/('package-'+c)/out,'usr/sbin/'+name,True)
copy(r/'build/package-openvpn/src/plugins/auth-pam/.libs/openvpn-plugin-auth-pam.so','usr/lib/arm-linux-gnueabi/openvpn-plugin-auth-pam.so',True)
for name in ['libcrypto.so.3','libssl.so.3']:copy(r/'build/openssl-armel'/name,'usr/lib/arm-linux-gnueabi/'+name,True)
copy(r/'build/openssl-armel/apps/openssl','usr/sbin/openssl',True)
copy(r/'build/openssl-armel/providers/legacy.so','usr/lib/arm-linux-gnueabi/ossl-modules/legacy.so',True)
# The real 1.1 libraries and unversioned development links remain with their
# existing BSP consumers. No shim and no unversioned .so.3 replacement is installed.
for name in ['libcrypto.so.1.1','libssl.so.1.1']:
 assert sha(root/'usr/lib/arm-linux-gnueabi'/name)==sha(base/'usr/lib/arm-linux-gnueabi'/name)
ss=r/'build/stage-strongswan'; assert ss.exists(), 'Build IPsec first'
shutil.rmtree(root/'usr/lib/arm-linux-gnueabi/ipsec')
shutil.rmtree(root/'usr/etc/strongswan.d')
for p in sorted((ss/'usr').rglob('*')):
 if p.is_file() and not p.is_symlink() and p.read_bytes()[:4]==b'\x7fELF':
  copy(p,str(p.relative_to(ss)),True)
 elif p.is_symlink() and str(p).endswith(('.so','.so.0')):
  dest=root/p.relative_to(ss);dest.parent.mkdir(parents=True,exist_ok=True);dest.unlink(missing_ok=True);dest.symlink_to(os.readlink(p))
 elif p.is_file() and '/ipsec/' in str(p) and p.suffix not in ('.a','.la'):
  copy(p,str(p.relative_to(ss)))
# The ipsec shell front-end embeds the configured multiarch executable directory.
copy(ss/'usr/sbin/ipsec','usr/sbin/ipsec')
for name in ['strongswan.conf','ipsec.conf']:
 if (ss/'etc'/name).exists():copy(ss/'etc'/name,'usr/etc/'+name,mode=0o644)
if (ss/'etc/strongswan.d').exists():shutil.copytree(ss/'etc/strongswan.d',root/'usr/etc/strongswan.d',dirs_exist_ok=True)
# Copy the complete model-selected, enumerated dictionary output as a unit.
shutil.rmtree(root/'www'); shutil.copytree(r/'build/webui-stage/www',root/'www',symlinks=True)
# Preserve any separate model themes produced by the original install recipe.
for p in (r/'build/webui-stage').iterdir():
 if p.name!='www':shutil.copytree(p,root/p.name,dirs_exist_ok=True,symlinks=True)
shutil.rmtree(root/'rom/easy-rsa')
shutil.copytree(source/'easy-rsa/easyrsa3',root/'rom/easy-rsa')
for p in (root/'rom/easy-rsa').rglob('*'):
 if p.is_file():p.chmod(0o755 if p.name=='easyrsa' else 0o644)
copy(source/'others/amtm','usr/sbin/amtm')
copy(source/'rom/apps_scripts/brcmsysinfo.sh','usr/sbin/brcmsysinfo.sh')
copy(source/'httpd/gencert.sh','usr/sbin/gencert.sh',mode=0o700)
# The configured board uses ECC certificate generation.
p=root/'usr/sbin/gencert.sh';p.write_text(p.read_text().replace('ECC256=0','ECC256=1'))
certs=(source/'rom/certs/ca-bundle.crt').read_text()
p=root/'rom/etc/ssl/certs/ca-certificates.crt'; p.write_text('\n'.join(re.findall(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----',certs,re.S))+'\n')
# Keep the USB multiarch layout, init and rollback policy exactly as tested.
manifest={'upstream':'96831be75b3b891f6aa4c608f00cc7bb2d499d67','version':'3006.102.9-beta1-leon1','base_checkpoint':parent.name,'kernel':'retained #36 4.19.294','openssl_policy':'3.5.8 standalone; real 1.1 BSP dependency closure retained','router_modified':False,'flashed':False}
(root/'usr/share/leon-upstream.json').write_text(json.dumps(manifest,indent=2)+'\n')
before=inventory(base); after=inventory(root)
modules=[n for n in before if n.endswith('.ko')];assert len(modules)==182 and all(after[n]==before[n] for n in modules)
for n in ['usr/sbin/init','usr/lib/systemd/systemd','usr/libexec/leon-rc-broker','usr/lib/arm-linux-gnueabi/libnvram.so']:
 assert after[n]==before[n],n
for row in installed: row['sha256']=sha(root/row['path'])
report=dict(manifest,installed=installed,changed=[n for n in before if n in after and before[n]!=after[n]],added=sorted(after.keys()-before.keys()),removed=sorted(before.keys()-after.keys()),modules_unchanged=len(modules))
(r/'evidence/production-staging.json').write_text(json.dumps(report,indent=2)+'\n')
print('STAGED',len(installed),'compiled/assets; changed',len(report['changed']),'added',len(report['added']),'removed',len(report['removed']))
