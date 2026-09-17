#!/usr/bin/env python3
"""Compare feature/API sets, run upstream tests, and replay the #36 crypto VM."""
import gzip, hashlib, json, os, shlex, subprocess, time
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent
old=w/'userspace-refresh-20260917';build=r/'build/openssl-oz-lto'
feature_cmd=['perl','-I.','-Mconfigdata','-MJSON::PP','-e','print encode_json(\\%disabled)']
before=json.loads(subprocess.check_output(feature_cmd,cwd=old/'build/openssl4'))
after=json.loads(subprocess.check_output(feature_cmd,cwd=build))
assert before==after, 'Configured feature set changed'
def api(path):
    lines=subprocess.check_output(['readelf','--dyn-syms','--wide',str(path)],text=True).splitlines()
    return sorted({f[-1] for line in lines if len(f:=line.split())>=8 and f[0].endswith(':') and f[6]!='UND' and f[4] in ('GLOBAL','WEAK')})
for name in ['libcrypto.so.4','libssl.so.4']:
    assert api(old/'overlay/usr/lib/aarch64-linux-gnu'/name)==api(r/'overlay/usr/lib/aarch64-linux-gnu'/name),name
loader=old/'sdk/lib/ld-linux-aarch64.so.1'
libs=':'.join(map(str,[build,old/'sdk/usr/lib/aarch64-linux-gnu',old/'sdk/lib/aarch64-linux-gnu']))
wrapper=r/'build/run-test';wrapper.write_text('#!/bin/sh\nexec '+shlex.join([str(loader),'--library-path',libs])+' "$@"\n');wrapper.chmod(0o755)
cmd=['make','-j8','test','TESTS=test_evp test_evp_extra test_rand test_ec test_rsa test_x509 test_ssl_new']
start=time.monotonic()
with (r/'evidence/upstream-tests.log').open('w') as log:
    p=subprocess.run(cmd,cwd=build,env=dict(os.environ,EXE_SHELL=str(wrapper),LC_ALL='C'),stdout=log,stderr=subprocess.STDOUT)
record={'features_identical':True,'exported_apis_identical':True,'command':cmd,
        'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-start,'router_modified':False}
(r/'evidence/optimized-tests.json').write_text(json.dumps(record,indent=2)+'\n')
print((r/'evidence/upstream-tests.log').read_text()[-2500:],flush=True)
assert p.returncode==0
original=old/'build/crypto-qemu-v2/guest.cpio.gz'
assert hashlib.sha256(original.read_bytes()).hexdigest()=='c10000e1d1878419b8939b81cbcd4ac1d87245d28072ed4c5c8b3aebea45ffda'
raw=gzip.decompress(original.read_bytes());pos=0;entries=[];replaced=[]
mapping=json.loads((r/'evidence/optimized-build.json').read_text())['files']
while pos<len(raw):
    fields=[int(raw[pos+6+8*i:pos+14+8*i],16) for i in range(13)]
    name=raw[pos+110:pos+109+fields[11]].decode();start=(pos+110+fields[11]+3)&~3
    data=raw[start:start+fields[6]]
    if name in mapping:
        data=(r/'overlay'/name).read_bytes();fields[6]=len(data);replaced.append(name)
    entries.append((fields,name,data))
    if name=='TRAILER!!!':break
    # Advance using the original size, even after replacing this entry.
    original_size=int(raw[pos+54:pos+62],16)
    pos=(start+original_size+3)&~3
assert set(replaced)==set(mapping)
out=bytearray()
for fields,name,data in entries:
    out+=b'070701'+''.join(f'{v:08x}' for v in fields).encode()+name.encode()+b'\0'
    out+=b'\0'*(-len(out)%4);out+=data;out+=b'\0'*(-len(out)%4)
guest=r/'build/optimized-crypto.cpio.gz';guest.write_bytes(gzip.compress(out,compresslevel=1,mtime=0))
(r/'scripts/run-crypto-qemu.py').write_text((old/'scripts/run-crypto-qemu.py').read_text())
subprocess.run(['python3',str(r/'scripts/run-crypto-qemu.py'),'--label','optimized-crypto',
                '--kernel',str(w/'multiarch-loader-20260916/saved-inputs/Image36'),
                '--initrd',str(guest)],check=True)
