#!/usr/bin/env python3
import os,json,subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parents[1];b=r/'build/systemd';prefix=[str(r/'sdk/lib/ld-linux-aarch64.so.1'),'--library-path',':'.join(map(str,[b/'src/shared',r/'sdk/usr/lib/aarch64-linux-gnu',r/'sdk/lib/aarch64-linux-gnu']))]
env=dict(os.environ,OPENSSL_CONF='/dev/null',OPENSSL_MODULES=str(r.parent/'rootfs-slim-20260917/build/rootfs/usr/lib/aarch64-linux-gnu/ossl-modules'))
records=[]
for name in ['test-openssl','test-compress','test-cryptolib']:
 start=time.monotonic()
 with (r/'evidence'/f'{name}.log').open('w') as log:p=subprocess.run(prefix+[str(b/name)],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=60)
 records.append({'name':name,'exit_code':p.returncode,'seconds':time.monotonic()-start})
 if p.returncode:print((r/'evidence'/f'{name}.log').read_text()[-3000:]);raise SystemExit(p.returncode)
(r/'evidence/native-systemd-tests.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records,indent=2))
