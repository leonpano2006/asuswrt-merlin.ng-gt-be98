#!/usr/bin/env python3
import subprocess,json
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent
prefix=[str(w/'userspace-refresh-20260917/sdk/lib/ld-linux-aarch64.so.1'),'--library-path',str(r/'build/rootfs/usr/lib/aarch64-linux-gnu')]
b=r/'build/sqlite-tests';b.mkdir(exist_ok=False)
old=w/'armhf-usb-20260917/build/rootfs/usr/gnu/bin/sqlite3';new=r/'build/sqlite/sqlite3'
sql='''.bail on
pragma journal_mode=WAL;
create table t(id integer primary key, payload text);
begin; insert into t values(1,'committed'); commit;
begin; insert into t values(2,'rolled back'); rollback;
select * from t;
create virtual table search using fts5(body);
insert into search values('GT BE98 container network');
select rowid,body from search where search match 'container';
create virtual table bounds using rtree(id,x1,x2,y1,y2);
insert into bounds values(1,0,5,0,5);
select id from bounds where x1<=3 and x2>=3;
select json_extract('{"cgroup":[1,2]}','$.cgroup[1]');
select count(*) from dbstat;
pragma integrity_check;
'''
results={}
for label,p in [('old',old),('new',new)]:
 db=b/(label+'.db');res=subprocess.run(prefix+[str(p),str(db)],input=sql,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
 results[label]=res.stdout
 reopened=subprocess.check_output(prefix+[str(p),str(db),'select count(*) from t; pragma integrity_check;'],text=True)
 assert reopened=='1\nok\n'
assert results['old']==results['new']
record={'results':results,'transaction_rollback_wal_fts5_rtree_json_dbstat_integrity_reopen_passed':True}
(r/'evidence/sqlite-tests.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
