#!/usr/bin/env python3
"""Retain the tested 257.13 service profile and enable selected native dependencies."""
import json,os,subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent;old=w/'systemd-upgrade-20260917'
cross=r/'configs/aarch64-sysroot.ini';cross.write_text((old/'configs/aarch64-sysroot.ini').read_text().replace(str(old),str(r)))
base=json.loads((old/'evidence/systemd-commands.json').read_text())['commands'][0]
options=[x for x in base if x.startswith(('--prefix=','--libdir=','--sysconfdir=','--localstatedir=','--buildtype=','-D'))]
options=[x for x in options if not x.startswith(('-Dversion-tag=','-Dtests='))]
options += ['-Dversion-tag=257.13-gt-be98-leon7','-Dtests=true','-Dopenssl=enabled','-Dcryptolib=openssl','-Dlibcurl=enabled','-Dzstd=enabled','-Dzlib=enabled','-Dblkid=enabled','-Ddefault-compression=zstd']
source=next((old/'sources').glob('systemd-*/'));build=r/'build/systemd';assert not build.exists()
env=dict(os.environ,PATH=str(w/'systemd-lab-20260916/host/bin')+':'+os.environ['PATH'],LC_ALL='C');env.pop('LD_LIBRARY_PATH',None);env.pop('PKG_CONFIG_PATH',None)
targets=['systemd','systemd-executor','systemd-shutdown','systemctl','systemd-journald','journalctl','systemd-notify','systemd-run','systemd-creds','systemd-sysctl','test-openssl','test-compress','test-cryptolib','test-sysctl-util']
commands=[['meson','setup',str(build),str(source),'--cross-file',str(cross)]+options,['ninja','-C',str(build),'-j4']+targets]
(r/'evidence/systemd-commands.json').write_text(json.dumps({'commands':commands,'enabled':['openssl','libcurl','zstd','zlib','blkid'],'production_units_unchanged':True},indent=2)+'\n')
for label,cmd in zip(['configure','build'],commands):
 print('SYSTEMD_'+label.upper(),flush=True)
 with (r/'evidence'/f'systemd-{label}.log').open('w') as log:ret=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 if ret.returncode:print((r/'evidence'/f'systemd-{label}.log').read_text()[-6000:]);raise SystemExit(ret.returncode)
print('SYSTEMD_FEATURE_BUILD_PASS')
