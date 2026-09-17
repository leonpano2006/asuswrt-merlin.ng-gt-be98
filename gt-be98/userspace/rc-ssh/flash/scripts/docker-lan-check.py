#!/usr/bin/env python3
"""Verify the labelled test container's LAN port before and after SSH restart."""
import argparse, hashlib, json
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--phase',choices=('before','after'),required=True);a=p.parse_args()
out=Path(__file__).resolve().parents[1]/'evidence/docker-lan-port.json'
s=requests.Session();s.trust_env=False
r=s.get('http://192.168.100.10:18099/',timeout=15);r.raise_for_status()
assert r.text.strip()=='GT-BE98-rmerlin-upstream-network-ok'
record=json.loads(out.read_text()) if out.exists() else {'expected_body':True,'phases':{}}
record['phases'][a.phase]={'status':r.status_code,'sha256':hashlib.sha256(r.content).hexdigest()}
out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
