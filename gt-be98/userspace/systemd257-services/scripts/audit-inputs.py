#!/usr/bin/env python3
"""Hash and save external rc dependencies instead of assuming an isolated tree."""
from pathlib import Path
import json,shlex,shutil
from common import sha
r=Path(__file__).resolve().parents[1];w=r.parent
src=w/'rmerlin-integration-20260916/source-tree/release/src/router/rc'
inputs=set()
for dep in (r/'build/rc').glob('*.d'):
    text=dep.read_text().replace('\\\n',' ')
    for name in shlex.split(text.split(':',1)[1]):
        p=Path(name)
        if not p.is_absolute():p=src/p
        inputs.add(p)
build=json.loads((r/'evidence/rc-build.json').read_text())
for name in build['retained_objects']:inputs.add(w/name)
for p in (w/'rmerlin-integration-20260916/build/management-libs').glob('*.so*'):
    if p.is_file():inputs.add(p)
records={}
for p in sorted(inputs):
    key=str(p.relative_to(w));records[key]={'sha256':sha(p),'bytes':p.stat().st_size}
    dst=r/'saved-inputs/dependencies'/key;dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():dst.unlink()
    shutil.copy2(p,dst,follow_symlinks=True)
record={'files':records,'count':len(records),
    'parent_git_commit':'0f9e311424bcaacc118f581d3602ba15ec2675dc',
    'requires_parent_checkpoints':['rmerlin-integration-20260916','rmerlin-ipsec-fix-20260916',
        'rmerlin-httpd-fix-20260917','systemd-lab-20260916','a53-runtimes-20260916',
        'gcc162-usb','leon-cgroup-20260915','multiarch-loader-20260916'],
    'notes':'Full SDK saved privately; GCC toolchains remain dependencies, not firmware-repository binaries'}
(r/'evidence/external-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
print('EXTERNAL_DEPENDENCIES_SAVED',len(records))
