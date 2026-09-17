#!/usr/bin/env python3
import hashlib,json,subprocess,tarfile
from pathlib import Path
r=Path(__file__).resolve().parents[1]
records=json.loads((r/'configs/sources.json').read_text())
(r/'sources').mkdir(exist_ok=True)
for name,record in records.items():
 url=record['url']
 p=r/'sources'/name
 if not p.exists():subprocess.run(['curl','--fail','--location','--retry','2','--max-time','120',url,'-o',str(p)],check=True)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256'],name
 assert p.stat().st_size==record['bytes'],name
 with tarfile.open(p) as t:
  names=t.getnames(); top=names[0].split('/')[0]
  assert top==record['directory']
  if not (r/'sources'/top).exists():t.extractall(r/'sources',filter='data')
print(json.dumps(records,indent=2))
