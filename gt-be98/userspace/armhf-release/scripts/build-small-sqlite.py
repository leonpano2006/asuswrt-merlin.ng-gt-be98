#!/usr/bin/env python3
"""Rebuild the existing SQLite CLI with the same engine options for size."""
import hashlib,json,os,subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent
src=w/'rmerlin-integration-20260916/source-tree/release/src/router/sqlite'
assert '#define SQLITE_VERSION        "3.42.0"' in (src/'sqlite3.h').read_text()
old=w/'armhf-usb-20260917/build/rootfs/usr/gnu/bin/sqlite3'
sdk=w/'userspace-refresh-20260917/sdk';loader=sdk/'lib/ld-linux-aarch64.so.1';libs=str(sdk/'lib/aarch64-linux-gnu')
def run_sqlite(path,sql):return subprocess.check_output([str(loader),'--library-path',libs,str(path),':memory:',sql],text=True)
options=run_sqlite(old,'pragma compile_options;').splitlines()
defs=['-DSQLITE_'+x for x in options if x.startswith('ENABLE_')]+['-DSQLITE_THREADSAFE=1']
build=r/'build/sqlite';build.mkdir(exist_ok=False);out=build/'sqlite3'
cmd=[str(w/'userspace-refresh-20260917/build/cc'),'-Oz','-flto=4','-g','-frecord-gcc-switches','-fstack-protector-strong','-Wl,--build-id=sha1,-z,relro,-z,now',*defs,str(src/'shell.c'),str(src/'sqlite3.c'),'-lm','-ldl','-lpthread','-o',str(out)]
start=time.monotonic()
with (r/'evidence/sqlite-build.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run(['aarch64-linux-gnu-strip','--strip-unneeded',str(out)],check=True)
new=run_sqlite(out,'pragma compile_options;').splitlines();oldhelp=run_sqlite(old,'.help -all');newhelp=run_sqlite(out,'.help -all')
record={'command':cmd,'source_sha256':{n:hashlib.sha256((src/n).read_bytes()).hexdigest() for n in ['shell.c','sqlite3.c','sqlite3.h']},'old_options':options,'new_options':new,'options_identical':options==new,'shell_help_identical':oldhelp==newhelp,'old_version':run_sqlite(old,'select sqlite_version(),sqlite_source_id();'),'new_version':run_sqlite(out,'select sqlite_version(),sqlite_source_id();'),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'seconds':time.monotonic()-start}
(r/'evidence/sqlite-build.json').write_text(json.dumps(record,indent=2)+'\n')
assert record['options_identical'] and record['shell_help_identical'] and record['old_version']==record['new_version']
print(json.dumps({k:v for k,v in record.items() if k not in ['command','old_options','new_options','source_sha256']},indent=2))
