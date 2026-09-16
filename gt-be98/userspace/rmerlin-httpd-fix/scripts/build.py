#!/usr/bin/env python3
"""Rebuild the faulty web translation object with the reviewed GCC 15 flags."""
from pathlib import Path
import json,os,subprocess,difflib,hashlib
r=Path(__file__).resolve().parents[1]; w=r.parent
p=w/'rmerlin-integration-20260916'
s=p/'source-tree/release/src/router/httpd/ej.c'
t=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env=dict(os.environ,LD_LIBRARY_PATH=t['host_library_dir'])
before=(r/'saved-inputs/ej.c').read_text(); after=s.read_text()
(r/'src/ej.c').write_text(after)
(r/'patches/httpd-translation-bounds.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/release/src/router/httpd/ej.c',tofile='b/release/src/router/httpd/ej.c')))
cmd=next(c[:] for c in json.loads((p/'build/management-httpd/compile-commands.json').read_text()) if str(s) in c)
cmd[cmd.index('-o')+1]=str(r/'build/ej.o');cmd[cmd.index('-MF')+1]=str(r/'build/ej.d')
link=json.loads((p/'build/management-httpd/link-command.json').read_text())
link[link.index('-o')+1]=str(r/'build/httpd');link[link.index(str(p/'build/management-httpd/ej.o'))]=str(r/'build/ej.o')
for name,c in [('compile-ej',cmd),('link-httpd',link)]:
 with (r/'evidence'/f'{name}.log').open('w') as log: subprocess.run(c,cwd=s.parent,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run([t['tools']+'strip','--strip-unneeded','-o',str(r/'build/httpd.stripped'),str(r/'build/httpd')],env=env,check=True)
(r/'build/httpd.stripped').chmod(0o755)
preamble='''#define _GNU_SOURCE\n#include <stdio.h>\n#include <string.h>\n#include <assert.h>\nstruct REPLACE_TAG_S { const char *org_name, *replace_name; };\n#define DUT_DOMAIN_NAME "router.asus.com"\nstatic char *nvram_safe_get(const char *key){return "GT-BE98";}\nstatic char *get_productid(void){return "GT-BE98";}\nstatic void replace_productid(char *src,char *dst,int n){strlcpy(dst,src,n);}\n'''
for name,src in [('tag-regression',after),('old-tag-reproducer',before)]:
 body=src[src.index('struct REPLACE_TAG_S replace_tag_string_t[]'):src.index('// Call this function if and only if we can read whole <#')]
 main=(r/'tests/tag-main.c').read_text() if name=='tag-regression' else 'int main(void){char out[2048]; puts(replace_tag_string("ZVDOMAIN_NAMEVZ",out,sizeof(out))); return 0;}\n'
 out=r/'build'/name
 (out.with_suffix('.c')).write_text(preamble+body+main)
 subprocess.run([t['cc'],'-O2','-D_FORTIFY_SOURCE=3','-fstack-protector-all','-frecord-gcc-switches','-Wl,--build-id=sha1',str(out.with_suffix('.c')),'-o',str(out)],env=env,check=True)
record={'compile':cmd,'link':link,'changed_object':'ej.o','fortify_source':3,'httpd_sha256':hashlib.sha256((r/'build/httpd.stripped').read_bytes()).hexdigest(),'retained_objects':{str(Path(a).relative_to(w)):hashlib.sha256(Path(a).read_bytes()).hexdigest() for a in link if a.endswith('.o') and a!=str(r/'build/ej.o')}}
(r/'evidence/build.json').write_text(json.dumps(record,indent=2)+'\n')
print('HTTPD_REBUILT',record['httpd_sha256'])
