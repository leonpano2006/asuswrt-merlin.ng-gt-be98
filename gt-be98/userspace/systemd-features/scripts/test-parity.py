#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
r=Path(__file__).resolve().parents[1];run=str(r/'build/run-target')
old=r.parent/'armhf-release-20260917/build/rootfs';new=r/'build/production-rootfs'
records={}
for name,rel,args in [('coreutils','usr/gnu/bin/coreutils',['--help']),
    ('bash-builtins','usr/bin/bash',['--noprofile','--norc','-c','enable -a']),
    ('bash-options','usr/bin/bash',['--noprofile','--norc','-c','shopt -p; true']),
    ('iperf-features','usr/bin/iperf3',['--version'])]:
    a=subprocess.check_output([run,str(old/rel)]+args,text=True).replace(str(old/rel),rel)
    b=subprocess.check_output([run,str(new/rel)]+args,text=True).replace(str(new/rel),rel)
    assert a==b,name
    records[name]={'same':True,'output':b}
def exports(p):
    with p.open('rb') as f:
        return {s.name for s in ELFFile(f).get_section_by_name('.dynsym').iter_symbols()
                if s['st_shndx']!='SHN_UNDEF' and s['st_info']['bind']=='STB_GLOBAL'}
baseline=json.loads((r/'configs/libcurl-public-api.json').read_text())
a=set(baseline['public'])
b=exports(new/'usr/lib/aarch64-linux-gnu/libcurl.so.4.8.0')
assert {x for x in a if x.startswith('curl_')}=={x for x in b if x.startswith('curl_')}
assert not any(x.startswith('Curl_') for x in b)
records['curl-exports']={'all_public_curl_symbols_preserved':True,'before':baseline['baseline_export_count'],'after':len(b),'public':sorted(b)}
(r/'evidence/feature-parity.json').write_text(json.dumps(records,indent=2)+'\n')
print({k:{a:b for a,b in v.items() if a not in ('output','public')} for k,v in records.items()})
