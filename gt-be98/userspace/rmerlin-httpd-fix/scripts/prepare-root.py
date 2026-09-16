#!/usr/bin/env python3
"""Overlay the fixed httpd on the tested IPsec-corrected production tree."""
from pathlib import Path
import json,shutil,subprocess
from common import inventory,sha
r=Path(__file__).resolve().parents[1];p=r.parent/'rmerlin-ipsec-fix-20260916';root=r/'build/production-rootfs';base=p/'build/production-rootfs'
assert sha(base/'usr/sbin/rc')=='7a8a660ed0dcc2e06fa9ed25518f4271ad42f85b08188bdad2425d34e2cc9f07'
if not root.exists():subprocess.run(['cp','-a','--reflink=auto',str(base),str(root)],check=True)
f=root/'usr/sbin/httpd';f.chmod(0o755);shutil.copy2(r/'build/httpd.stripped',f)
f=root/'usr/share/leon-upstream.json';d=json.loads(f.read_text());d.update(version='3006.102.9-beta1-leon3',correction='IPsec IFNAMSIZ interface storage and HTTPD translation bounds');f.chmod(0o644);f.write_text(json.dumps(d,indent=2)+'\n')
a=inventory(base);b=inventory(root);changed={k for k in a if a[k]!=b.get(k)};assert set(a)==set(b);assert changed=={'usr/sbin/httpd','usr/share/leon-upstream.json'},changed
(r/'build/probes').mkdir(exist_ok=True)
for probe in (p/'build/probes').iterdir():
 dst=r/'build/probes'/probe.name
 if dst.exists():dst.unlink()
 shutil.copy2(probe,dst)
shutil.copy2(r/'build/tag-regression',r/'build/probes/httpd-tag-regression')
f=r/'build/probes/upstream-check.sh';f.write_text(f.read_text().replace('echo LAB_UPSTREAM_ALL_PASS','/usr/libexec/httpd-tag-regression\necho LAB_UPSTREAM_ALL_PASS'))
(r/'evidence/production-delta.json').write_text(json.dumps({'parent':'rmerlin-ipsec-fix-20260916','changed_paths':sorted(changed),'httpd_sha256':sha(root/'usr/sbin/httpd'),'other_paths_unchanged':True},indent=2)+'\n')
