#!/usr/bin/env python3
"""Exercise dynamic CLI feature parity and cross-decode with the original CLI."""
import hashlib,json,subprocess,random
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent
root=r/'build/rootfs';libs=root/'usr/lib/aarch64-linux-gnu'
prefix=[str(w/'userspace-refresh-20260917/sdk/lib/ld-linux-aarch64.so.1'),'--library-path',str(libs)]
old=w/'armhf-usb-20260917/build/rootfs/usr/bin/zstd';new=r/'build/zstd-dynamic-full/zstd'
b=r/'build/zstd-test-full';b.mkdir(exist_ok=True)
def run(p,args,data=None,check=True):return subprocess.run(prefix+[str(p),*map(str,args)],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=check)
assert run(old,['--help']).stdout==run(new,['--help']).stdout
rng=random.Random(53);data=(b'GT-BE98 A53 armhf external USB full zstd support\n'*5000)+rng.randbytes(32000)
records=[]
for args in [['-1'],['--ultra','-22','-T2'],['--format=gzip','-9']]:
 for enc,dec in [(new,old),(old,new)]:
  compressed=run(enc,args+['-q','-c'],data).stdout
  assert run(dec,['-q','-d','-c'],compressed).stdout==data
  records.append({'args':args,'encoder':enc.name if enc==new else 'original','compressed_bytes':len(compressed)})
corrupt=bytearray(run(new,['-q','-c'],data).stdout);corrupt[-1]^=255
assert run(new,['-q','-d','-c'],bytes(corrupt),check=False).returncode!=0
samples=b/'samples';samples.mkdir()
for i in range(80): (samples/f'{i:03}.txt').write_bytes((f'router-record-{i:03} '.encode()+data[i:i+1000])*3)
dictionary=b/'dictionary';run(new,['--train',*sorted(samples.iterdir()),'-o',dictionary,'--maxdict=4096'])
compressed=run(new,['-q','-c','-D',dictionary],data).stdout
assert run(old,['-q','-d','-c','-D',dictionary],compressed).stdout==data
record={'help_identical':True,'cross_decode':records,'dictionary_training_and_cross_decode':True,'corruption_rejected':True,'new_sha256':hashlib.sha256(new.read_bytes()).hexdigest()}
(r/'evidence/zstd-tests.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
